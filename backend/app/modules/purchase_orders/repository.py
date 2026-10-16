"""
app/modules/purchase_orders/repository.py — Database operations for Purchase Orders.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.modules.spend.models import PurchaseOrder


class PurchaseOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_po_number(self, org_id: uuid.UUID) -> str:
        """Generate next sequential PO number in format PO-YYYY-NNNN."""
        year = date.today().year
        prefix = f"PO-{year}-"
        stmt = select(func.count()).where(
            PurchaseOrder.org_id == org_id,
            PurchaseOrder.po_number.like(f"{prefix}%"),
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return f"{prefix}{str(count + 1).zfill(4)}"

    async def get_by_id(
        self, po_id: uuid.UUID, org_id: uuid.UUID
    ) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.company),
                selectinload(PurchaseOrder.receipts),
                selectinload(PurchaseOrder.material_request),
                selectinload(PurchaseOrder.rfx_event),
                selectinload(PurchaseOrder.rfx_response),
            )
            .where(
                PurchaseOrder.id == po_id,
                PurchaseOrder.org_id == org_id,
                PurchaseOrder.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_po_number(
        self, po_number: str, org_id: uuid.UUID
    ) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.company),
                selectinload(PurchaseOrder.receipts),
            )
            .where(
                PurchaseOrder.po_number.ilike(po_number.strip()),
                PurchaseOrder.org_id == org_id,
                PurchaseOrder.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        org_id: uuid.UUID,
        *,
        status: str | None = None,
        company_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[PurchaseOrder], int]:
        base = select(PurchaseOrder).where(
            PurchaseOrder.org_id == org_id,
            PurchaseOrder.deleted_at.is_(None),
        )
        if status:
            base = base.where(PurchaseOrder.status == status)
        if company_id:
            base = base.where(PurchaseOrder.company_id == company_id)
        if search:
            search_clause = f"%{search}%"
            base = base.where(
                or_(
                    PurchaseOrder.po_number.ilike(search_clause),
                    PurchaseOrder.notes.ilike(search_clause),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        items_stmt = (
            base.options(
                joinedload(PurchaseOrder.company),
                selectinload(PurchaseOrder.receipts),
            )
            .order_by(PurchaseOrder.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        pos = (await self.db.execute(items_stmt)).scalars().all()
        return pos, total

    async def create(self, po: PurchaseOrder) -> PurchaseOrder:
        self.db.add(po)
        await self.db.flush()
        return po

    async def update(self, po: PurchaseOrder) -> PurchaseOrder:
        await self.db.flush()
        return po
