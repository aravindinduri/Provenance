"""
app/modules/approvals/repository.py — Data access for approval engine.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approvals.models import ApprovalRule, ApprovalStep, ApprovalWorkflow


class ApprovalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Rules ────────────────────────────────────────────────────────────────

    async def get_rules(
        self, org_id: uuid.UUID, document_type: str
    ) -> Sequence[ApprovalRule]:
        stmt = (
            select(ApprovalRule)
            .where(
                ApprovalRule.org_id == org_id,
                ApprovalRule.document_type == document_type,
                ApprovalRule.is_active == True,  # noqa: E712
            )
            .order_by(ApprovalRule.priority)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def create_rule(self, org_id: uuid.UUID, **kwargs) -> ApprovalRule:
        rule = ApprovalRule(org_id=org_id, **kwargs)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def list_rules(self, org_id: uuid.UUID) -> Sequence[ApprovalRule]:
        stmt = select(ApprovalRule).where(ApprovalRule.org_id == org_id).order_by(ApprovalRule.priority)
        return (await self.db.execute(stmt)).scalars().all()

    # ── Workflows ─────────────────────────────────────────────────────────────

    async def get_workflow_for_document(
        self, org_id: uuid.UUID, document_type: str, document_id: uuid.UUID
    ) -> ApprovalWorkflow | None:
        stmt = select(ApprovalWorkflow).where(
            ApprovalWorkflow.org_id == org_id,
            ApprovalWorkflow.document_type == document_type,
            ApprovalWorkflow.document_id == document_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_workflow_by_id(
        self, workflow_id: uuid.UUID, org_id: uuid.UUID
    ) -> ApprovalWorkflow | None:
        stmt = select(ApprovalWorkflow).where(
            ApprovalWorkflow.id == workflow_id,
            ApprovalWorkflow.org_id == org_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_pending_for_user(
        self,
        org_id: uuid.UUID,
        user_role: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[ApprovalWorkflow], int]:
        """List workflows where the current step has a pending step matching user_role."""
        filters = [
            ApprovalWorkflow.org_id == org_id,
            ApprovalWorkflow.status == "pending",
            ApprovalStep.status == "pending",
            ApprovalStep.step_number == ApprovalWorkflow.current_step,
        ]
        if user_role and user_role.lower() != "all":
            filters.append(ApprovalStep.approver_role == user_role)

        stmt = (
            select(ApprovalWorkflow)
            .join(ApprovalStep, ApprovalStep.workflow_id == ApprovalWorkflow.id)
            .where(*filters)
            .distinct()
        )
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(ApprovalWorkflow.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def create_workflow(
        self,
        org_id: uuid.UUID,
        document_type: str,
        document_id: uuid.UUID,
        initiated_by: str | None,
    ) -> ApprovalWorkflow:
        from datetime import datetime, timezone
        wf = ApprovalWorkflow(
            org_id=org_id,
            document_type=document_type,
            document_id=document_id,
            initiated_by=initiated_by,
            initiated_at=datetime.now(timezone.utc),
            status="pending",
            current_step=1,
            created_by=initiated_by,
        )
        self.db.add(wf)
        await self.db.flush()
        return wf

    async def create_step(
        self,
        workflow: ApprovalWorkflow,
        *,
        step_number: int,
        approver_role: str,
    ) -> ApprovalStep:
        step = ApprovalStep(
            org_id=workflow.org_id,
            workflow_id=workflow.id,
            step_number=step_number,
            approver_role=approver_role,
            status="pending",
        )
        self.db.add(step)
        await self.db.flush()
        return step

    async def record_decision(
        self,
        step: ApprovalStep,
        action: str,
        comments: str | None,
        user_id: str | None,
    ) -> ApprovalStep:
        from datetime import datetime, timezone
        step.status = action
        step.decision_at = datetime.now(timezone.utc)
        step.comments = comments
        step.approver_id = user_id
        step.updated_by = user_id
        await self.db.flush()
        return step

    async def complete_workflow(
        self, workflow: ApprovalWorkflow, status: str
    ) -> ApprovalWorkflow:
        from datetime import datetime, timezone
        workflow.status = status
        workflow.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(workflow)
        return workflow
