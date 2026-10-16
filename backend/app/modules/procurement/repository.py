"""
app/modules/procurement/repository.py — Data access for material requests.

mr_number generation is deterministic: MR-{YEAR}-{sequence padded to 4}.
Sequence is computed from max existing number per org — no separate sequence table needed.
ponytail: COUNT-based sequence is O(n) per org but trivially fast at any real-world volume.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence as Seq
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.procurement.models import MaterialRequest, MaterialRequestItem


class ProcurementRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── MR number generation ──────────────────────────────────────────────────

    async def next_mr_number(self, org_id: uuid.UUID) -> str:
        """Generate next MR number in format MR-YYYY-NNNN."""
        year = date.today().year
        prefix = f"MR-{year}-"
        stmt = select(func.count()).where(
            MaterialRequest.org_id == org_id,
            MaterialRequest.mr_number.like(f"{prefix}%"),
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return f"{prefix}{str(count + 1).zfill(4)}"

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def get_by_id(self, mr_id: uuid.UUID, org_id: uuid.UUID) -> MaterialRequest | None:
        stmt = select(MaterialRequest).where(
            MaterialRequest.id == mr_id,
            MaterialRequest.org_id == org_id,
            MaterialRequest.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        org_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Seq[MaterialRequest], int]:
        base = select(MaterialRequest).where(
            MaterialRequest.org_id == org_id,
            MaterialRequest.deleted_at.is_(None),
        )
        if status:
            base = base.where(MaterialRequest.status == status)

        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                base.order_by(MaterialRequest.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def create(
        self,
        org_id: uuid.UUID,
        *,
        mr_number: str,
        title: str,
        requested_by: str | None,
        required_by_date: date | None,
        priority: str,
        department: str | None,
        justification: str | None,
        currency: str | None,
        created_by: str | None,
    ) -> MaterialRequest:
        mr = MaterialRequest(
            org_id=org_id,
            mr_number=mr_number,
            title=title,
            status="draft",
            requested_by=requested_by,
            required_by_date=required_by_date,
            priority=priority,
            department=department,
            justification=justification,
            currency=currency,
            created_by=created_by,
        )
        self.db.add(mr)
        await self.db.flush()
        return mr

    async def add_line_items(
        self,
        mr: MaterialRequest,
        line_items: list[dict],
        org_id: uuid.UUID,
    ) -> None:
        for li in line_items:
            item = MaterialRequestItem(
                org_id=org_id,
                material_request_id=mr.id,
                **li,
            )
            self.db.add(item)
        await self.db.flush()
        await self.db.refresh(mr)

    async def update_status(self, mr: MaterialRequest, status: str) -> MaterialRequest:
        mr.status = status
        await self.db.flush()
        await self.db.refresh(mr)
        return mr

    async def update(self, mr: MaterialRequest, updates: dict, *, updated_by: str | None = None) -> MaterialRequest:
        for k, v in updates.items():
            setattr(mr, k, v)
        if updated_by:
            mr.updated_by = updated_by
        await self.db.flush()
        await self.db.refresh(mr)
        return mr

    async def soft_delete(self, mr: MaterialRequest) -> None:
        from datetime import datetime, timezone
        mr.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def recalc_total(self, mr: MaterialRequest) -> None:
        """Recompute total_estimated_amount from line items."""
        total = sum(
            (li.estimated_unit_price or 0) * float(li.quantity)
            for li in (mr.line_items or [])
            if li.estimated_unit_price and li.deleted_at is None
        )
        mr.total_estimated_amount = total if total else None
        await self.db.flush()
