"""
app/modules/procurement/service.py — Business logic for material requests.

Approval routing is triggered on submit() via ApprovalService.
All state transitions are deterministic.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.procurement.models import MaterialRequest
from app.modules.procurement.repository import ProcurementRepository
from app.modules.procurement.schemas import (
    MaterialRequestCreate,
    MaterialRequestOut,
    MaterialRequestUpdate,
    PaginatedMaterialRequests,
)


_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["pending_approval", "cancelled"],
    "pending_approval": ["approved", "cancelled"],
    "approved": ["ordered", "partially_ordered", "cancelled"],
    "ordered": ["cancelled"],
    "partially_ordered": ["ordered", "cancelled"],
    "cancelled": [],
}


class MRNotFound(Exception):
    def __init__(self, mr_id: uuid.UUID) -> None:
        super().__init__(f"Material Request {mr_id} not found")
        self.mr_id = mr_id


class InvalidStatusTransition(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition MR from '{current}' to '{target}'")


class ProcurementService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProcurementRepository(db)

    async def list_mrs(
        self,
        org_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedMaterialRequests:
        rows, total = await self.repo.list(org_id, status=status, limit=limit, offset=offset)
        return PaginatedMaterialRequests(
            items=[MaterialRequestOut.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_mr(self, mr_id: uuid.UUID, org_id: uuid.UUID) -> MaterialRequest:
        mr = await self.repo.get_by_id(mr_id, org_id)
        if not mr:
            raise MRNotFound(mr_id)
        return mr

    async def create_mr(
        self,
        org_id: uuid.UUID,
        data: MaterialRequestCreate,
        *,
        user_id: str | None = None,
    ) -> MaterialRequest:
        mr_number = await self.repo.next_mr_number(org_id)
        mr = await self.repo.create(
            org_id,
            mr_number=mr_number,
            title=data.title,
            requested_by=user_id,
            required_by_date=data.required_by_date,
            priority=data.priority,
            department=data.department,
            justification=data.justification,
            currency=data.currency,
            created_by=user_id,
        )
        if data.line_items:
            line_dicts = [li.model_dump() for li in data.line_items]
            await self.repo.add_line_items(mr, line_dicts, org_id)
            await self.repo.recalc_total(mr)

        await self.db.commit()
        await self.db.refresh(mr)
        return mr

    async def update_mr(
        self,
        mr_id: uuid.UUID,
        org_id: uuid.UUID,
        data: MaterialRequestUpdate,
        *,
        user_id: str | None = None,
    ) -> MaterialRequest:
        mr = await self.get_mr(mr_id, org_id)
        if mr.status not in ("draft",):
            raise InvalidStatusTransition(mr.status, "update")
        updates = data.model_dump(exclude_unset=True)
        mr = await self.repo.update(mr, updates, updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(mr)
        return mr

    async def submit_mr(
        self,
        mr_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        user_id: str | None = None,
    ) -> MaterialRequest:
        """Move MR from draft → pending_approval and trigger approval workflow."""
        mr = await self.get_mr(mr_id, org_id)
        self._assert_transition(mr.status, "pending_approval")
        mr = await self.repo.update_status(mr, "pending_approval")

        # Trigger approval engine
        from app.modules.approvals.service import ApprovalService
        approval_svc = ApprovalService(self.db)
        await approval_svc.initiate(
            org_id=org_id,
            document_type="material_request",
            document_id=mr.id,
            amount=float(mr.total_estimated_amount or 0),
            currency=mr.currency or "USD",
            initiated_by=user_id,
        )

        await self.db.commit()
        await self.db.refresh(mr)
        return mr

    async def cancel_mr(
        self, mr_id: uuid.UUID, org_id: uuid.UUID, *, user_id: str | None = None
    ) -> MaterialRequest:
        mr = await self.get_mr(mr_id, org_id)
        self._assert_transition(mr.status, "cancelled")
        mr = await self.repo.update_status(mr, "cancelled")
        await self.db.commit()
        await self.db.refresh(mr)
        return mr

    def _assert_transition(self, current: str, target: str) -> None:
        if target not in _VALID_TRANSITIONS.get(current, []):
            raise InvalidStatusTransition(current, target)
