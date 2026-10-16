"""
app/modules/goods_receipts/service.py — Goods Receipt Note (GRN) business logic & PO fulfillment tracking.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.goods_receipts.repository import GoodsReceiptRepository
from app.modules.goods_receipts.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptOut,
    GoodsReceiptUpdate,
    PaginatedGoodsReceipts,
)
from app.modules.purchase_orders.repository import PurchaseOrderRepository
from app.modules.purchase_orders.service import PONotFound, PurchaseOrderService

logger = structlog.get_logger(__name__)


class GoodsReceiptNotFound(Exception):
    pass


class InvalidGRNStatusTransition(Exception):
    pass


class GoodsReceiptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GoodsReceiptRepository(db)
        self.po_repo = PurchaseOrderRepository(db)

    def _format_grn_out(self, grn: GoodsReceipt) -> GoodsReceiptOut:
        po_number = None
        supplier_name = None
        if hasattr(grn, "purchase_order") and grn.purchase_order:
            po_number = grn.purchase_order.po_number
            if hasattr(grn.purchase_order, "company") and grn.purchase_order.company:
                supplier_name = getattr(grn.purchase_order.company, "legal_name", None)

        return GoodsReceiptOut(
            id=grn.id,
            org_id=grn.org_id,
            grn_number=grn.grn_number,
            purchase_order_id=grn.purchase_order_id,
            po_number=po_number,
            supplier_name=supplier_name,
            received_date=grn.received_date,
            received_by=grn.received_by,
            status=grn.status,
            line_items=grn.line_items if isinstance(grn.line_items, list) else [],
            delivery_note_ref=grn.delivery_note_ref,
            carrier=grn.carrier,
            notes=grn.notes,
            created_at=grn.created_at,
        )

    async def create_receipt(
        self,
        org_id: uuid.UUID,
        data: GoodsReceiptCreate,
        *,
        user_id: str | None = None,
    ) -> GoodsReceiptOut:
        # Verify purchase order
        po = await self.po_repo.get_by_id(data.purchase_order_id, org_id)
        if not po:
            raise PONotFound(f"Purchase order {data.purchase_order_id} not found.")

        # PO must be approved, sent, acknowledged, or partially_received to record receipt
        receivable_statuses = {"approved", "sent", "acknowledged", "partially_received"}
        if po.status not in receivable_statuses:
            raise InvalidGRNStatusTransition(
                f"Cannot record goods receipt against purchase order with status '{po.status}'. "
                f"Must be one of: {', '.join(receivable_statuses)}."
            )

        grn_number = await self.repo.next_grn_number(org_id)

        # Build validated line items
        line_items_dict: list[dict[str, Any]] = []
        for item in data.line_items:
            line_items_dict.append(
                {
                    "po_line_index": item.po_line_index,
                    "item_id": str(item.item_id) if item.item_id else None,
                    "item_code": item.item_code,
                    "description": item.description,
                    "qty_received": float(item.qty_received),
                    "qty_rejected": float(item.qty_rejected),
                    "unit_of_measure": item.unit_of_measure or "each",
                    "inspection_notes": item.inspection_notes,
                }
            )

        grn = GoodsReceipt(
            org_id=org_id,
            grn_number=grn_number,
            purchase_order_id=po.id,
            received_date=data.received_date or date.today(),
            received_by=data.received_by or user_id or "Receiving Dock",
            status="draft",
            line_items=line_items_dict,
            delivery_note_ref=data.delivery_note_ref,
            carrier=data.carrier,
            notes=data.notes,
            created_by=user_id,
        )

        grn = await self.repo.create(grn)
        logger.info(
            "goods_receipt_created",
            grn_number=grn.grn_number,
            po_number=po.po_number,
            org_id=str(org_id),
        )

        if data.auto_confirm:
            return await self.confirm_receipt(grn.id, org_id, user_id=user_id)

        # Re-fetch with relations
        fetched = await self.repo.get_by_id(grn.id, org_id)
        return self._format_grn_out(fetched or grn)

    async def confirm_receipt(
        self,
        grn_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
    ) -> GoodsReceiptOut:
        """
        Confirm a Goods Receipt Note and dynamically evaluate PO fulfillment status.
        Updates PO status to 'received' (if all items completely fulfilled) or
        'partially_received' (if some goods still pending).
        """
        grn = await self.repo.get_by_id(grn_id, org_id)
        if not grn:
            raise GoodsReceiptNotFound(f"Goods receipt {grn_id} not found.")

        if grn.status in ("confirmed", "partial"):
            # Already confirmed
            return self._format_grn_out(grn)

        po = await self.po_repo.get_by_id(grn.purchase_order_id, org_id)
        if not po:
            raise PONotFound(f"Linked purchase order {grn.purchase_order_id} not found.")

        # Determine all confirmed GRNs for this PO plus this current one
        all_receipts = await self.repo.get_receipts_for_po(po.id, org_id)
        
        # Cumulative received quantities by line index
        cumulative_qty: dict[int, float] = {}
        for r in all_receipts:
            # Include confirmed receipts and the one being confirmed right now
            if r.status in ("confirmed", "partial") or r.id == grn.id:
                for line in (r.line_items if isinstance(r.line_items, list) else []):
                    idx = int(line.get("po_line_index", 0))
                    qty_rec = float(line.get("qty_received", 0.0))
                    cumulative_qty[idx] = cumulative_qty.get(idx, 0.0) + qty_rec

        # Check PO line items
        po_lines = po.line_items if isinstance(po.line_items, list) else []
        is_fully_fulfilled = True
        has_any_fulfillment = False

        for idx, po_item in enumerate(po_lines):
            ordered = float(po_item.get("quantity", 0.0))
            received = cumulative_qty.get(idx, 0.0)
            if received > 0:
                has_any_fulfillment = True
            if received < ordered:
                is_fully_fulfilled = False

        # If PO has no lines or all lines met
        if len(po_lines) > 0 and is_fully_fulfilled:
            po.status = "received"
            grn.status = "confirmed"
            logger.info("po_fully_received", po_number=po.po_number)
        elif has_any_fulfillment:
            po.status = "partially_received"
            grn.status = "partial"
            logger.info("po_partially_received", po_number=po.po_number)
        else:
            grn.status = "confirmed"

        grn.updated_by = user_id
        po.updated_by = user_id

        await self.repo.update(grn)
        await self.po_repo.update(po)

        refetched = await self.repo.get_by_id(grn.id, org_id)
        return self._format_grn_out(refetched or grn)

    async def get_receipt(
        self, grn_id: uuid.UUID, org_id: uuid.UUID
    ) -> GoodsReceiptOut:
        grn = await self.repo.get_by_id(grn_id, org_id)
        if not grn:
            raise GoodsReceiptNotFound(f"Goods receipt {grn_id} not found.")
        return self._format_grn_out(grn)

    async def list_receipts(
        self,
        org_id: uuid.UUID,
        *,
        purchase_order_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedGoodsReceipts:
        grns, total = await self.repo.list(
            org_id,
            purchase_order_id=purchase_order_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [self._format_grn_out(g) for g in grns]
        return PaginatedGoodsReceipts(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def cancel_receipt(
        self, grn_id: uuid.UUID, org_id: uuid.UUID, *, user_id: str | None = None
    ) -> None:
        grn = await self.repo.get_by_id(grn_id, org_id)
        if not grn:
            raise GoodsReceiptNotFound(f"Goods receipt {grn_id} not found.")
        if grn.status in ("confirmed", "partial"):
            raise InvalidGRNStatusTransition("Cannot cancel an already confirmed goods receipt.")

        grn.deleted_at = datetime.now(timezone.utc)
        grn.updated_by = user_id
        await self.repo.update(grn)
