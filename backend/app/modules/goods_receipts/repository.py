"""
app/modules/goods_receipts/repository.py — Database operations for Goods Receipt Notes (GRN).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.spend.models import PurchaseOrder


class GoodsReceiptRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_grn_number(self, org_id: uuid.UUID) -> str:
        """Generate next sequential GRN number in format GRN-YYYY-NNNN."""
        year = date.today().year
        prefix = f"GRN-{year}-"
        stmt = select(func.count()).where(
            GoodsReceipt.org_id == org_id,
            GoodsReceipt.grn_number.like(f"{prefix}%"),
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return f"{prefix}{str(count + 1).zfill(4)}"

    async def get_by_id(
        self, grn_id: uuid.UUID, org_id: uuid.UUID
    ) -> GoodsReceipt | None:
        stmt = (
            select(GoodsReceipt)
            .options(
                joinedload(GoodsReceipt.purchase_order).joinedload(PurchaseOrder.company)
            )
            .where(
                GoodsReceipt.id == grn_id,
                GoodsReceipt.org_id == org_id,
                GoodsReceipt.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        org_id: uuid.UUID,
        *,
        purchase_order_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[GoodsReceipt], int]:
        base = select(GoodsReceipt).where(
            GoodsReceipt.org_id == org_id,
            GoodsReceipt.deleted_at.is_(None),
        )
        if purchase_order_id:
            base = base.where(GoodsReceipt.purchase_order_id == purchase_order_id)
        if status:
            base = base.where(GoodsReceipt.status == status)
        if search:
            search_clause = f"%{search}%"
            base = base.where(
                or_(
                    GoodsReceipt.grn_number.ilike(search_clause),
                    GoodsReceipt.delivery_note_ref.ilike(search_clause),
                    GoodsReceipt.carrier.ilike(search_clause),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        items_stmt = (
            base.options(
                joinedload(GoodsReceipt.purchase_order).joinedload(PurchaseOrder.company)
            )
            .order_by(GoodsReceipt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        grns = (await self.db.execute(items_stmt)).scalars().all()
        return grns, total

    async def get_receipts_for_po(
        self, po_id: uuid.UUID, org_id: uuid.UUID
    ) -> Sequence[GoodsReceipt]:
        stmt = select(GoodsReceipt).where(
            GoodsReceipt.purchase_order_id == po_id,
            GoodsReceipt.org_id == org_id,
            GoodsReceipt.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def create(self, grn: GoodsReceipt) -> GoodsReceipt:
        self.db.add(grn)
        await self.db.flush()
        return grn

    async def update(self, grn: GoodsReceipt) -> GoodsReceipt:
        await self.db.flush()
        return grn
