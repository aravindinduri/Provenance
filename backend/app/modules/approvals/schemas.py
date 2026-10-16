"""
app/modules/approvals/schemas.py — Pydantic schemas for the approval engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ApprovalStepOut(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    step_number: int
    approver_id: str | None = None
    approver_role: str | None = None
    status: str
    decision_at: datetime | None = None
    comments: str | None = None
    delegated_to: str | None = None

    model_config = {"from_attributes": True}


class ApprovalWorkflowOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    document_type: str
    document_id: uuid.UUID
    current_step: int
    status: str
    initiated_by: str | None = None
    initiated_at: datetime | None = None
    completed_at: datetime | None = None
    steps: list[ApprovalStepOut] = []

    model_config = {"from_attributes": True}


class ApprovalRuleCreate(BaseModel):
    document_type: str
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str | None = None
    required_role: str
    auto_approve_below: float | None = None
    priority: int = 10


class ApprovalRuleOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    document_type: str
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str | None = None
    required_role: str
    auto_approve_below: float | None = None
    is_active: bool
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveRejectAction(BaseModel):
    action: Literal["approve", "reject"]
    comments: str | None = None


class PaginatedApprovalWorkflows(BaseModel):
    items: list[ApprovalWorkflowOut]
    total: int
    limit: int
    offset: int
