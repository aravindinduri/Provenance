"""
/v1/approvals — Approval queue and decision

GET  /approvals/queue             pending workflows for current user's role
GET  /approvals/workflows/{id}    get workflow detail
POST /approvals/workflows/{id}/decide  approve or reject current step
GET  /approvals/rules             list DoA rules
POST /approvals/rules             create DoA rule

GET  /approvals/document/{type}/{document_id}   workflow for a specific document
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.approvals.schemas import (
    ApprovalRuleCreate,
    ApprovalRuleOut,
    ApprovalWorkflowOut,
    ApproveRejectAction,
    PaginatedApprovalWorkflows,
)
from app.modules.approvals.service import (
    ApprovalService,
    NotPendingStep,
    WorkflowNotFound,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _svc(db: AsyncSession = Depends(get_db)) -> ApprovalService:
    return ApprovalService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("/queue", response_model=PaginatedApprovalWorkflows)
async def approval_queue(
    role: str = Query(..., description="Approver role to filter pending workflows"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ApprovalService = Depends(_svc),
) -> PaginatedApprovalWorkflows:
    return await svc.list_pending_for_role(
        _org_id(current_user), role, limit=limit, offset=offset
    )


@router.get("/workflows/{workflow_id}", response_model=ApprovalWorkflowOut)
async def get_workflow(
    workflow_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ApprovalService = Depends(_svc),
) -> ApprovalWorkflowOut:
    from app.modules.approvals.repository import ApprovalRepository
    repo = ApprovalRepository(svc.db)
    wf = await repo.get_workflow_by_id(workflow_id, _org_id(current_user))
    if not wf:
        raise not_found("Approval workflow not found")
    return ApprovalWorkflowOut.model_validate(wf)


@router.post("/workflows/{workflow_id}/decide", response_model=ApprovalWorkflowOut)
async def decide(
    workflow_id: uuid.UUID,
    data: ApproveRejectAction,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ApprovalService = Depends(_svc),
) -> ApprovalWorkflowOut:
    try:
        wf = await svc.decide(
            workflow_id=workflow_id,
            org_id=_org_id(current_user),
            action=data.action,
            user_id=current_user.user_id,
            comments=data.comments,
        )
    except WorkflowNotFound:
        raise not_found("Approval workflow not found")
    except NotPendingStep as exc:
        raise bad_request(str(exc))
    return ApprovalWorkflowOut.model_validate(wf)


@router.get("/document/{document_type}/{document_id}", response_model=ApprovalWorkflowOut)
async def get_document_workflow(
    document_type: str,
    document_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ApprovalService = Depends(_svc),
) -> ApprovalWorkflowOut:
    wf = await svc.get_workflow_for_document(_org_id(current_user), document_type, document_id)
    if not wf:
        raise not_found("No approval workflow found for this document")
    return ApprovalWorkflowOut.model_validate(wf)


@router.get("/rules", response_model=list[ApprovalRuleOut])
async def list_rules(
    current_user: CurrentUser = Depends(get_current_user),
    svc: ApprovalService = Depends(_svc),
) -> list[ApprovalRuleOut]:
    return await svc.list_rules(_org_id(current_user))


@router.post("/rules", response_model=ApprovalRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: ApprovalRuleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ApprovalService = Depends(_svc),
) -> ApprovalRuleOut:
    return await svc.create_rule(_org_id(current_user), data, user_id=current_user.user_id)
