"""
app/modules/approvals/service.py — Generic approval engine.

Routing is 100% deterministic:
  1. Load approval_rules for (org, document_type) ordered by priority.
  2. Find matching rule(s) by amount range.
  3. If amount < auto_approve_below → auto-approve immediately.
  4. Otherwise create workflow + steps per matching rules.
  5. Advance: approve current step → move to next, or complete workflow.
  6. Reject: reject current step → complete workflow as rejected.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approvals.models import ApprovalWorkflow
from app.modules.approvals.repository import ApprovalRepository
from app.modules.approvals.schemas import (
    ApprovalRuleCreate,
    ApprovalRuleOut,
    ApprovalWorkflowOut,
    PaginatedApprovalWorkflows,
)

logger = structlog.get_logger(__name__)


class WorkflowNotFound(Exception):
    def __init__(self, workflow_id: uuid.UUID) -> None:
        super().__init__(f"Approval workflow {workflow_id} not found")


class NotPendingStep(Exception):
    pass


class ApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ApprovalRepository(db)

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate(
        self,
        *,
        org_id: uuid.UUID,
        document_type: str,
        document_id: uuid.UUID,
        amount: float,
        currency: str,
        initiated_by: str | None,
    ) -> ApprovalWorkflow:
        """
        Evaluate DoA rules and create a workflow.
        Returns auto-approved workflow immediately if no human step required.
        """
        rules = await self.repo.get_rules(org_id, document_type)

        # Auto-approve check: if any rule's auto_approve_below > amount, skip human
        for rule in rules:
            if rule.auto_approve_below is not None and amount < float(rule.auto_approve_below):
                logger.info(
                    "approval_auto_approved",
                    document_type=document_type,
                    document_id=str(document_id),
                    amount=amount,
                )
                wf = await self.repo.create_workflow(org_id, document_type, document_id, initiated_by)
                wf = await self.repo.complete_workflow(wf, "approved")
                await self.db.flush()
                return wf

        # Determine matching rules by amount range
        matching = [
            r for r in rules
            if (r.min_amount is None or amount >= float(r.min_amount))
            and (r.max_amount is None or amount <= float(r.max_amount))
        ]

        wf = await self.repo.create_workflow(org_id, document_type, document_id, initiated_by)

        if not matching:
            # No rule configured → auto-approve (open/no DoA configured)
            logger.warning(
                "approval_no_rule_match",
                document_type=document_type,
                amount=amount,
                org_id=str(org_id),
            )
            wf = await self.repo.complete_workflow(wf, "approved")
            await self._sync_document_status(document_type, document_id, "approved")
        else:
            for idx, rule in enumerate(matching, start=1):
                await self.repo.create_step(wf, step_number=idx, approver_role=rule.required_role)
            await self.db.flush()
            await self.db.refresh(wf)

        return wf

    async def _sync_document_status(
        self, document_type: str, document_id: uuid.UUID, outcome: str
    ) -> None:
        """Propagate terminal approval outcome to the source document."""
        if document_type == "material_request":
            from app.modules.procurement.models import MaterialRequest
            mr = await self.db.get(MaterialRequest, document_id)
            if mr:
                mr.status = "approved" if outcome == "approved" else "draft"
                await self.db.flush()

    # ── Decide ────────────────────────────────────────────────────────────────

    async def decide(
        self,
        *,
        workflow_id: uuid.UUID,
        org_id: uuid.UUID,
        action: str,
        user_id: str | None,
        comments: str | None,
    ) -> ApprovalWorkflow:
        """Approve or reject the current pending step."""
        wf = await self.repo.get_workflow_by_id(workflow_id, org_id)
        if not wf:
            raise WorkflowNotFound(workflow_id)

        # Find the current pending step
        current_steps = [s for s in wf.steps if s.step_number == wf.current_step and s.status == "pending"]
        if not current_steps:
            raise NotPendingStep(f"No pending step at position {wf.current_step}")

        step = current_steps[0]
        await self.repo.record_decision(step, action, comments, user_id)

        if action == "reject":
            wf = await self.repo.complete_workflow(wf, "rejected")
            await self._sync_document_status(wf.document_type, wf.document_id, "rejected")
        else:
            # Advance to next step or complete
            next_step_number = wf.current_step + 1
            next_steps = [s for s in wf.steps if s.step_number == next_step_number]
            if next_steps:
                wf.current_step = next_step_number
                await self.db.flush()
            else:
                wf = await self.repo.complete_workflow(wf, "approved")
                await self._sync_document_status(wf.document_type, wf.document_id, "approved")

        await self.db.flush()
        await self.db.refresh(wf)
        return wf

    # ── Query ─────────────────────────────────────────────────────────────────

    async def get_workflow_for_document(
        self,
        org_id: uuid.UUID,
        document_type: str,
        document_id: uuid.UUID,
    ) -> ApprovalWorkflow | None:
        return await self.repo.get_workflow_for_document(org_id, document_type, document_id)

    async def list_pending_for_role(
        self,
        org_id: uuid.UUID,
        user_role: str,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedApprovalWorkflows:
        rows, total = await self.repo.list_pending_for_user(
            org_id, user_role, limit=limit, offset=offset
        )
        return PaginatedApprovalWorkflows(
            items=[ApprovalWorkflowOut.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    # ── Rules CRUD ────────────────────────────────────────────────────────────

    async def list_rules(self, org_id: uuid.UUID) -> list[ApprovalRuleOut]:
        rules = await self.repo.list_rules(org_id)
        return [ApprovalRuleOut.model_validate(r) for r in rules]

    async def create_rule(
        self, org_id: uuid.UUID, data: ApprovalRuleCreate, *, user_id: str | None = None
    ) -> ApprovalRuleOut:
        rule = await self.repo.create_rule(
            org_id,
            created_by=user_id,
            **data.model_dump(),
        )
        await self.db.commit()
        await self.db.refresh(rule)
        return ApprovalRuleOut.model_validate(rule)
