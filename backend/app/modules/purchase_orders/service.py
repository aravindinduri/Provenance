"""
app/modules/purchase_orders/service.py — Purchase Order lifecycle and business logic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approvals.service import ApprovalService
from app.modules.purchase_orders.repository import PurchaseOrderRepository
from app.modules.purchase_orders.schemas import (
    GRNSummaryOut,
    PaginatedPurchaseOrders,
    POLineItemCreate,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    PurchaseOrderUpdate,
)
from app.modules.spend.models import PurchaseOrder

logger = structlog.get_logger(__name__)

_VALID_PO_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["pending_approval", "cancelled"],
    "pending_approval": ["approved", "draft", "cancelled"],
    "approved": ["sent", "cancelled"],
    "sent": ["acknowledged", "partially_received", "received", "cancelled"],
    "acknowledged": ["partially_received", "received", "cancelled"],
    "partially_received": ["received", "closed", "cancelled"],
    "received": ["closed"],
    "closed": [],
    "cancelled": [],
}


class PONotFound(Exception):
    pass


class InvalidPOStatusTransition(Exception):
    pass


class PurchaseOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PurchaseOrderRepository(db)

    def _assert_transition(self, current: str, target: str) -> None:
        allowed = _VALID_PO_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise InvalidPOStatusTransition(
                f"Cannot transition purchase order from '{current}' to '{target}'. "
                f"Allowed transitions: {allowed or 'none (terminal state)'}."
            )

    def _format_po_out(self, po: PurchaseOrder) -> PurchaseOrderOut:
        # Calculate line items total and enrich received quantities if available
        raw_items = po.line_items if isinstance(po.line_items, list) else []
        enriched_items: list[dict[str, Any]] = []

        # Tally received quantities across confirmed/partial goods receipts
        receipt_qty_map: dict[int, tuple[float, float]] = {}
        receipts = getattr(po, "receipts", []) or []
        for grn in receipts:
            if getattr(grn, "deleted_at", None):
                continue
            grn_items = grn.line_items if isinstance(grn.line_items, list) else []
            for item in grn_items:
                idx = int(item.get("po_line_index", 0))
                rec = float(item.get("qty_received", 0.0))
                rej = float(item.get("qty_rejected", 0.0))
                curr_rec, curr_rej = receipt_qty_map.get(idx, (0.0, 0.0))
                receipt_qty_map[idx] = (curr_rec + rec, curr_rej + rej)

        for idx, item in enumerate(raw_items):
            q_rec, q_rej = receipt_qty_map.get(idx, (0.0, 0.0))
            enriched = dict(item)
            enriched["po_line_index"] = idx
            enriched["qty_received"] = q_rec
            enriched["qty_rejected"] = q_rej
            enriched_items.append(enriched)

        grn_summaries = [
            GRNSummaryOut(
                id=g.id,
                grn_number=g.grn_number,
                received_date=g.received_date,
                received_by=g.received_by,
                status=g.status,
                delivery_note_ref=g.delivery_note_ref,
                carrier=g.carrier,
                line_items=g.line_items if isinstance(g.line_items, list) else [],
                created_at=g.created_at,
            )
            for g in receipts
            if not getattr(g, "deleted_at", None)
        ]

        company_name = None
        if hasattr(po, "company") and po.company:
            company_name = getattr(po.company, "legal_name", None)

        delivery_addr = (
            po.delivery_address if isinstance(po.delivery_address, dict) else None
        )

        return PurchaseOrderOut(
            id=po.id,
            org_id=po.org_id,
            po_number=po.po_number,
            company_id=po.company_id,
            company_name=company_name,
            contract_id=po.contract_id,
            material_request_id=po.material_request_id,
            rfx_event_id=po.rfx_event_id,
            rfx_response_id=po.rfx_response_id,
            order_date=po.order_date,
            expected_delivery_date=po.expected_delivery_date,
            total_amount=float(po.total_amount or 0.0),
            currency=po.currency or "USD",
            line_items=enriched_items,
            status=po.status,
            approved_by=po.approved_by,
            approved_at=po.approved_at,
            sent_at=po.sent_at,
            acknowledged_at=po.acknowledged_at,
            delivery_address=delivery_addr,
            payment_terms=po.payment_terms,
            delivery_terms=po.delivery_terms,
            notes=po.notes,
            created_at=po.created_at,
            receipt_count=len(grn_summaries),
            receipts=grn_summaries,
        )

    async def create_po(
        self,
        org_id: uuid.UUID,
        data: PurchaseOrderCreate,
        *,
        user_id: str | None = None,
    ) -> PurchaseOrderOut:
        po_number = await self.repo.next_po_number(org_id)

        # Calculate line item prices and total
        total_amount = 0.0
        line_items_dict: list[dict[str, Any]] = []
        for idx, item in enumerate(data.line_items):
            line_tot = (
                item.total_price
                if item.total_price is not None
                else round(item.quantity * item.unit_price, 2)
            )
            total_amount += line_tot
            line_items_dict.append(
                {
                    "po_line_index": idx,
                    "item_id": str(item.item_id) if item.item_id else None,
                    "item_code": item.item_code,
                    "description": item.description,
                    "quantity": float(item.quantity),
                    "unit_of_measure": item.unit_of_measure or "each",
                    "unit_price": float(item.unit_price),
                    "total_price": float(line_tot),
                    "qty_received": 0.0,
                    "qty_rejected": 0.0,
                }
            )

        delivery_dict = (
            data.delivery_address.model_dump()
            if hasattr(data.delivery_address, "model_dump")
            else data.delivery_address
        )

        po = PurchaseOrder(
            org_id=org_id,
            po_number=po_number,
            company_id=data.company_id,
            contract_id=data.contract_id,
            material_request_id=data.material_request_id,
            rfx_event_id=data.rfx_event_id,
            rfx_response_id=data.rfx_response_id,
            order_date=data.order_date or date.today(),
            expected_delivery_date=data.expected_delivery_date,
            total_amount=round(total_amount, 2),
            currency=data.currency or "USD",
            line_items=line_items_dict,
            status="draft",
            delivery_address=delivery_dict,
            payment_terms=data.payment_terms,
            delivery_terms=data.delivery_terms,
            notes=data.notes,
            created_by=user_id,
        )

        po = await self.repo.create(po)
        logger.info("purchase_order_created", po_number=po.po_number, org_id=str(org_id))
        return self._format_po_out(po)

    async def get_po(self, po_id: uuid.UUID, org_id: uuid.UUID) -> PurchaseOrderOut:
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        return self._format_po_out(po)

    async def list_pos(
        self,
        org_id: uuid.UUID,
        *,
        status: str | None = None,
        company_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedPurchaseOrders:
        pos, total = await self.repo.list(
            org_id,
            status=status,
            company_id=company_id,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [self._format_po_out(p) for p in pos]
        return PaginatedPurchaseOrders(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        data: PurchaseOrderUpdate,
        *,
        user_id: str | None = None,
    ) -> PurchaseOrderOut:
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        if po.status != "draft":
            raise InvalidPOStatusTransition("Only draft purchase orders can be edited.")

        if data.company_id is not None:
            po.company_id = data.company_id
        if data.order_date is not None:
            po.order_date = data.order_date
        if data.expected_delivery_date is not None:
            po.expected_delivery_date = data.expected_delivery_date
        if data.currency is not None:
            po.currency = data.currency
        if data.payment_terms is not None:
            po.payment_terms = data.payment_terms
        if data.delivery_terms is not None:
            po.delivery_terms = data.delivery_terms
        if data.notes is not None:
            po.notes = data.notes
        if data.delivery_address is not None:
            po.delivery_address = (
                data.delivery_address.model_dump()
                if hasattr(data.delivery_address, "model_dump")
                else data.delivery_address
            )

        if data.line_items is not None:
            total_amount = 0.0
            line_items_dict: list[dict[str, Any]] = []
            for idx, item in enumerate(data.line_items):
                line_tot = (
                    item.total_price
                    if item.total_price is not None
                    else round(item.quantity * item.unit_price, 2)
                )
                total_amount += line_tot
                line_items_dict.append(
                    {
                        "po_line_index": idx,
                        "item_id": str(item.item_id) if item.item_id else None,
                        "item_code": item.item_code,
                        "description": item.description,
                        "quantity": float(item.quantity),
                        "unit_of_measure": item.unit_of_measure or "each",
                        "unit_price": float(item.unit_price),
                        "total_price": float(line_tot),
                        "qty_received": 0.0,
                        "qty_rejected": 0.0,
                    }
                )
            po.line_items = line_items_dict
            po.total_amount = round(total_amount, 2)

        po.updated_by = user_id
        await self.repo.update(po)
        return self._format_po_out(po)

    async def submit_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
    ) -> PurchaseOrderOut:
        """Submit draft PO for approval, routing through DoA rules engine."""
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        self._assert_transition(po.status, "pending_approval")

        approval_svc = ApprovalService(self.db)
        wf = await approval_svc.initiate(
            org_id=org_id,
            document_type="purchase_order",
            document_id=po.id,
            amount=float(po.total_amount or 0.0),
            currency=po.currency or "USD",
            initiated_by=user_id,
        )

        now = datetime.now(timezone.utc)
        if wf.status == "approved":
            po.status = "approved"
            po.approved_by = "auto-approved:doa-threshold"
            po.approved_at = now
            logger.info("purchase_order_auto_approved", po_number=po.po_number)
        else:
            po.status = "pending_approval"
            logger.info("purchase_order_submitted_for_approval", po_number=po.po_number)

        po.updated_by = user_id
        await self.repo.update(po)
        return self._format_po_out(po)

    async def approve_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
        comments: str | None = None,
    ) -> PurchaseOrderOut:
        """Manually or rule-based approve a pending purchase order."""
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        self._assert_transition(po.status, "approved")

        po.status = "approved"
        po.approved_by = user_id or "approved"
        po.approved_at = datetime.now(timezone.utc)
        po.updated_by = user_id

        # Update approval workflow if active
        approval_svc = ApprovalService(self.db)
        wf = await approval_svc.get_workflow_for_document(org_id, "purchase_order", po.id)
        if wf and wf.status == "pending":
            try:
                await approval_svc.decide(
                    workflow_id=wf.id,
                    org_id=org_id,
                    action="approve",
                    user_id=user_id,
                    comments=comments,
                )
            except Exception as exc:
                logger.warning("po_approval_workflow_sync_failed", error=str(exc))

        await self.repo.update(po)
        logger.info("purchase_order_approved", po_number=po.po_number, user_id=user_id)
        return self._format_po_out(po)

    async def send_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
    ) -> PurchaseOrderOut:
        """Mark purchase order as officially dispatched/sent to vendor."""
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        self._assert_transition(po.status, "sent")

        po.status = "sent"
        po.sent_at = datetime.now(timezone.utc)
        po.updated_by = user_id
        await self.repo.update(po)
        logger.info("purchase_order_sent", po_number=po.po_number)
        return self._format_po_out(po)

    async def acknowledge_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
    ) -> PurchaseOrderOut:
        """Mark purchase order as acknowledged by the vendor."""
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        self._assert_transition(po.status, "acknowledged")

        po.status = "acknowledged"
        po.acknowledged_at = datetime.now(timezone.utc)
        po.updated_by = user_id
        await self.repo.update(po)
        logger.info("purchase_order_acknowledged", po_number=po.po_number)
        return self._format_po_out(po)

    async def cancel_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
        reason: str | None = None,
    ) -> PurchaseOrderOut:
        """Cancel a purchase order."""
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        self._assert_transition(po.status, "cancelled")

        po.status = "cancelled"
        if reason:
            po.notes = f"{po.notes or ''}\n[Cancellation Reason]: {reason}".strip()
        po.updated_by = user_id
        await self.repo.update(po)
        logger.info("purchase_order_cancelled", po_number=po.po_number)
        return self._format_po_out(po)

    async def close_po(
        self,
        po_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
    ) -> PurchaseOrderOut:
        """Close a completed purchase order."""
        po = await self.repo.get_by_id(po_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {po_id} not found.")
        self._assert_transition(po.status, "closed")

        po.status = "closed"
        po.updated_by = user_id
        await self.repo.update(po)
        logger.info("purchase_order_closed", po_number=po.po_number)
        return self._format_po_out(po)
