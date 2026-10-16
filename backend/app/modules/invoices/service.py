"""
app/modules/invoices/service.py — Purchase Invoice & 3-Way Match business logic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.models import Company
from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.invoices.matching_engine import (
    MatchTolerances,
    evaluate_invoice_match,
)
from app.modules.invoices.models import Invoice
from app.modules.invoices.repository import InvoiceRepository
from app.modules.invoices.schemas import (
    InvoiceCreate,
    InvoiceMatchResult,
    InvoiceOut,
    InvoicePayRequest,
    InvoiceStatsOut,
    InvoiceUpdate,
    PaginatedInvoices,
)
from app.modules.spend.models import PurchaseOrder

logger = structlog.get_logger(__name__)


class InvoiceNotFound(Exception):
    pass


class InvalidInvoiceState(Exception):
    pass


class InvoiceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = InvoiceRepository(db)

    def _format_invoice_out(self, inv: Invoice) -> InvoiceOut:
        supplier_name = None
        if hasattr(inv, "company") and inv.company:
            supplier_name = getattr(inv.company, "legal_name", None)

        po_number = None
        if hasattr(inv, "purchase_order") and inv.purchase_order:
            po_number = getattr(inv.purchase_order, "po_number", None)
            if not supplier_name and hasattr(inv.purchase_order, "company") and inv.purchase_order.company:
                supplier_name = getattr(inv.purchase_order.company, "legal_name", None)

        grn_number = None
        if hasattr(inv, "goods_receipt") and inv.goods_receipt:
            grn_number = getattr(inv.goods_receipt, "grn_number", None)

        raw_exceptions = inv.match_exceptions
        exceptions_list: list[dict[str, Any]] = []
        if isinstance(raw_exceptions, list):
            exceptions_list = raw_exceptions
        elif isinstance(raw_exceptions, dict):
            exceptions_list = [raw_exceptions]

        raw_lines = inv.line_items
        lines_list: list[dict[str, Any]] = raw_lines if isinstance(raw_lines, list) else []

        return InvoiceOut(
            id=inv.id,
            org_id=inv.org_id,
            invoice_number=inv.invoice_number or f"INV-{str(inv.id)[:8].upper()}",
            company_id=inv.company_id,
            supplier_name=supplier_name,
            po_id=inv.po_id,
            po_number=po_number,
            goods_receipt_id=inv.goods_receipt_id,
            grn_number=grn_number,
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            amount=float(inv.amount),
            currency=inv.currency,
            category=inv.category,
            payment_status=inv.payment_status or "unpaid",
            match_status=inv.match_status or "unmatched",
            match_exceptions=exceptions_list,
            approved_by=inv.approved_by,
            approved_at=inv.approved_at,
            paid_at=inv.paid_at,
            line_items=lines_list,
            notes=inv.notes,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    async def create_invoice(
        self,
        org_id: uuid.UUID,
        data: InvoiceCreate,
        *,
        user_id: str | None = None,
    ) -> InvoiceOut:
        # Validate or resolve linked Purchase Order
        po: PurchaseOrder | None = None
        if data.po_id:
            stmt = select(PurchaseOrder).where(
                PurchaseOrder.id == data.po_id,
                PurchaseOrder.org_id == org_id,
                PurchaseOrder.deleted_at.is_(None),
            )
            po = (await self.db.execute(stmt)).scalar_one_or_none()
            if not po:
                raise InvalidInvoiceState(f"Purchase order {data.po_id} not found for this tenant.")

        # Validate or resolve linked Goods Receipt
        grn: GoodsReceipt | None = None
        if data.goods_receipt_id:
            stmt_grn = select(GoodsReceipt).where(
                GoodsReceipt.id == data.goods_receipt_id,
                GoodsReceipt.org_id == org_id,
                GoodsReceipt.deleted_at.is_(None),
            )
            grn = (await self.db.execute(stmt_grn)).scalar_one_or_none()
            if not grn:
                raise InvalidInvoiceState(f"Goods receipt {data.goods_receipt_id} not found.")

        # If PO has receipts and no GRN was explicitly specified, find latest confirmed GRN
        if po and not grn:
            stmt_latest_grn = (
                select(GoodsReceipt)
                .where(
                    GoodsReceipt.purchase_order_id == po.id,
                    GoodsReceipt.org_id == org_id,
                    GoodsReceipt.status.in_(["confirmed", "partial"]),
                    GoodsReceipt.deleted_at.is_(None),
                )
                .order_by(GoodsReceipt.created_at.desc())
                .limit(1)
            )
            grn = (await self.db.execute(stmt_latest_grn)).scalar_one_or_none()

        # Resolve vendor
        company_id = data.company_id
        if not company_id and po and po.company_id:
            company_id = po.company_id
        elif not company_id and data.supplier_name:
            stmt_comp = (
                select(Company.id)
                .where(
                    Company.legal_name.ilike(f"%{data.supplier_name.strip()}%"),
                    Company.deleted_at.is_(None),
                )
                .limit(1)
            )
            company_id = (await self.db.execute(stmt_comp)).scalar_one_or_none()

        # Generate sequential invoice number if not provided
        invoice_number = data.invoice_number
        if not invoice_number or not invoice_number.strip():
            invoice_number = await self.repo.next_invoice_number(org_id)

        # Build line items
        line_items_dict: list[dict[str, Any]] = []
        if data.line_items:
            for idx, li in enumerate(data.line_items):
                tot = (
                    float(li.total_amount)
                    if li.total_amount is not None
                    else round(float(li.quantity) * float(li.unit_price), 2)
                )
                line_items_dict.append(
                    {
                        "po_line_index": li.po_line_index or idx,
                        "item_id": str(li.item_id) if li.item_id else None,
                        "item_code": li.item_code,
                        "description": li.description,
                        "quantity": float(li.quantity),
                        "unit_price": float(li.unit_price),
                        "total_amount": tot,
                        "unit_of_measure": li.unit_of_measure or "each",
                    }
                )
        elif po and isinstance(po.line_items, list):
            # Prepopulate lines directly from PO
            for idx, po_item in enumerate(po.line_items):
                qty = float(po_item.get("quantity", 1.0))
                prc = float(po_item.get("unit_price", 0.0))
                line_items_dict.append(
                    {
                        "po_line_index": idx,
                        "item_id": po_item.get("item_id"),
                        "item_code": po_item.get("item_code"),
                        "description": po_item.get("description", "Material Item"),
                        "quantity": qty,
                        "unit_price": prc,
                        "total_amount": round(qty * prc, 2),
                        "unit_of_measure": po_item.get("unit_of_measure", "each"),
                    }
                )

        # Compute total amount
        total_amount = data.amount
        if total_amount is None or total_amount <= 0:
            if line_items_dict:
                total_amount = round(sum(it["total_amount"] for it in line_items_dict), 2)
            elif po and po.total_amount:
                total_amount = float(po.total_amount)
            else:
                total_amount = 0.0

        inv_date = data.invoice_date or date.today()
        due_date = data.due_date or (inv_date + timedelta(days=30))

        invoice = Invoice(
            org_id=org_id,
            company_id=company_id,
            po_id=po.id if po else None,
            goods_receipt_id=grn.id if grn else None,
            invoice_number=invoice_number,
            amount=total_amount,
            currency=data.currency or (po.currency if po else "USD"),
            spend_date=inv_date,
            invoice_date=inv_date,
            due_date=due_date,
            category=data.category or (po.notes if po else None) or "Direct Procurement",
            payment_status="unpaid",
            match_status="unmatched",
            match_exceptions=[],
            line_items=line_items_dict,
            notes=data.notes,
            created_by=user_id,
        )

        await self.repo.create(invoice)
        await self.db.commit()

        # Automatically execute matching engine if linked to a PO
        if data.auto_match and po:
            try:
                await self.match_invoice(invoice.id, org_id, user_id=user_id)
            except Exception as exc:
                logger.warning("auto_match_invoice_failed", invoice_id=str(invoice.id), error=str(exc))

        # Re-fetch with all eager relationships loaded
        saved = await self.repo.get_by_id(invoice.id, org_id)
        return self._format_invoice_out(saved or invoice)

    async def get_invoice(self, invoice_id: uuid.UUID, org_id: uuid.UUID) -> InvoiceOut:
        inv = await self.repo.get_by_id(invoice_id, org_id)
        if not inv:
            raise InvoiceNotFound(f"Invoice {invoice_id} not found.")
        return self._format_invoice_out(inv)

    async def list_invoices(
        self,
        org_id: uuid.UUID,
        *,
        po_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        match_status: str | None = None,
        payment_status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedInvoices:
        items, total = await self.repo.list_invoices(
            org_id,
            po_id=po_id,
            company_id=company_id,
            match_status=match_status,
            payment_status=payment_status,
            search=search,
            limit=limit,
            offset=offset,
        )
        return PaginatedInvoices(
            items=[self._format_invoice_out(i) for i in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def match_invoice(
        self,
        invoice_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
        tolerances: MatchTolerances | None = None,
    ) -> InvoiceMatchResult:
        inv = await self.repo.get_by_id(invoice_id, org_id)
        if not inv:
            raise InvoiceNotFound(f"Invoice {invoice_id} not found.")

        po: PurchaseOrder | None = inv.purchase_order
        grn: GoodsReceipt | None = inv.goods_receipt

        # If PO is present but GRN not linked on the invoice, check if a GRN exists for the PO
        if po and not grn:
            stmt = (
                select(GoodsReceipt)
                .where(
                    GoodsReceipt.purchase_order_id == po.id,
                    GoodsReceipt.org_id == org_id,
                    GoodsReceipt.status.in_(["confirmed", "partial"]),
                    GoodsReceipt.deleted_at.is_(None),
                )
                .order_by(GoodsReceipt.created_at.desc())
                .limit(1)
            )
            found_grn = (await self.db.execute(stmt)).scalar_one_or_none()
            if found_grn:
                grn = found_grn
                inv.goods_receipt_id = found_grn.id

        result = evaluate_invoice_match(inv, po, grn, tolerances)

        # Persist match outcome
        inv.match_status = result.match_status
        inv.match_exceptions = [e.model_dump() for e in result.exceptions]

        if result.within_tolerance:
            inv.approved_by = "System Auto-Match"
            inv.approved_at = datetime.now(timezone.utc)

        await self.db.commit()

        logger.info(
            "invoice_match_evaluated",
            invoice_id=str(invoice.id if hasattr(invoice, 'id') else inv.id),
            match_status=result.match_status,
            exceptions_count=len(result.exceptions),
        )
        return result

    async def approve_invoice(
        self,
        invoice_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
        notes: str | None = None,
    ) -> InvoiceOut:
        inv = await self.repo.get_by_id(invoice_id, org_id)
        if not inv:
            raise InvoiceNotFound(f"Invoice {invoice_id} not found.")

        approver = user_id or "Authorized Approver"
        inv.approved_by = approver
        inv.approved_at = datetime.now(timezone.utc)

        # If it was in exception, update status to reflect manual override approval
        if inv.match_status == "exception":
            inv.notes = (
                f"{inv.notes or ''}\n[Override Approved by {approver} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}: {notes or 'Discrepancy reviewed and accepted.'}]"
            ).strip()

        await self.db.commit()
        return self._format_invoice_out(inv)

    async def record_payment(
        self,
        invoice_id: uuid.UUID,
        org_id: uuid.UUID,
        data: InvoicePayRequest,
        *,
        user_id: str | None = None,
    ) -> InvoiceOut:
        inv = await self.repo.get_by_id(invoice_id, org_id)
        if not inv:
            raise InvoiceNotFound(f"Invoice {invoice_id} not found.")

        pay_amt = data.amount if (data.amount is not None and data.amount > 0) else float(inv.amount)
        if pay_amt >= float(inv.amount):
            inv.payment_status = "paid"
            inv.paid_at = datetime.now(timezone.utc)
        else:
            inv.payment_status = "partially_paid"

        ref = data.payment_reference or f"TXN-{uuid.uuid4().hex[:8].upper()}"
        pay_note = f"[Payment of {inv.currency} {pay_amt:,.2f} recorded via {data.payment_method}. Ref: {ref}]"
        inv.notes = f"{inv.notes or ''}\n{pay_note}".strip()

        await self.db.commit()
        return self._format_invoice_out(inv)

    async def get_stats(self, org_id: uuid.UUID) -> InvoiceStatsOut:
        stats = await self.repo.get_stats(org_id)
        return InvoiceStatsOut(**stats)
