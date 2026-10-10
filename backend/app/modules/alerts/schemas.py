"""
Pydantic schemas for the alerts module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AlertEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    evidence_type: str
    source_record_id: uuid.UUID | None = None
    chunk_id: uuid.UUID | None = None
    source_url: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    retrieved_at: datetime | None = None
    excerpt: str | None = None
    payload: dict[str, Any] | None = None
    display_order: int = 0


class AlertActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    user_id: str
    action: str
    note: str | None = None
    created_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    risk_assessment_id: uuid.UUID
    event_id: uuid.UUID
    company_id: uuid.UUID
    headline: str
    explanation: str | None = None
    why_it_matters: str | None = None
    recommendations: list[Any] = Field(default_factory=list)
    severity_band: str
    impact_score: float
    confidence: float
    needs_human_judgment: bool = False
    target_personas: list[str] = Field(default_factory=list)
    category: str | None = None
    status: str
    dismissed_reason: str | None = None
    assigned_to: str | None = None
    explanation_model: str | None = None
    first_notified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Denormalized company details for fast UI rendering
    company_name: str | None = None
    company_country: str | None = None
    company_domain: str | None = None

    evidence: list[AlertEvidenceOut] = Field(default_factory=list)
    actions: list[AlertActionOut] = Field(default_factory=list)


class PaginatedAlerts(BaseModel):
    data: list[AlertOut]
    total: int
    limit: int
    offset: int


class AlertCountsOut(BaseModel):
    total: int = 0
    new: int = 0
    acknowledged: int = 0
    investigating: int = 0
    escalated: int = 0
    resolved: int = 0
    dismissed: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class AlertActionCreate(BaseModel):
    action: str = Field(..., description="Action type: acknowledged, investigating, escalated, dismissed, resolved")
    note: str | None = Field(default=None, description="Optional note or explanation for the action")


class AlertScanResponse(BaseModel):
    scanned_suppliers: int
    generated_alerts: int
    message: str
