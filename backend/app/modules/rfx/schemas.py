"""
app/modules/rfx/schemas.py — Pydantic schemas for RFx sourcing events, quotations, and bid comparison.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Shared Criterion Schema ──────────────────────────────────────────────────

class EvaluationCriterion(BaseModel):
    criterion: str = Field(..., min_length=1, description="e.g. Price, Quality, Delivery, Risk")
    weight: float = Field(..., ge=0, le=100, description="Percentage weight (e.g. 40 for 40%)")
    description: str | None = None


class EvaluationScore(BaseModel):
    criterion: str
    score: float = Field(..., ge=0, le=100, description="Score 0-100")
    notes: str | None = None


# ── Invitation Schemas ────────────────────────────────────────────────────────

class RFxInvitationCreate(BaseModel):
    supplier_id: uuid.UUID


class InviteSuppliersRequest(BaseModel):
    supplier_ids: list[uuid.UUID] = Field(..., min_length=1)


class RFxInvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfx_event_id: uuid.UUID
    supplier_id: uuid.UUID
    status: str
    invited_at: datetime
    responded_at: datetime | None = None
    supplier_legal_name: str | None = None
    supplier_country: str | None = None


# ── Response / Quotation Schemas ─────────────────────────────────────────────

class RFxResponseLineItem(BaseModel):
    item: str
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    lead_time_days: int | None = None


class RFxResponseCreate(BaseModel):
    rfx_event_id: uuid.UUID
    supplier_id: uuid.UUID
    total_amount: float | None = None
    currency: str = Field(default="USD", max_length=3)
    line_items: list[RFxResponseLineItem] = Field(..., min_length=1)
    validity_date: date | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    attachments: list[Any] | None = None
    source_document_id: uuid.UUID | None = None


class RFxResponseEvaluateRequest(BaseModel):
    scores: list[EvaluationScore] = Field(..., min_length=1)


class RFxResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfx_event_id: uuid.UUID
    supplier_id: uuid.UUID
    response_number: str
    total_amount: float
    currency: str
    line_items: list[dict[str, Any]]
    evaluation_scores: list[dict[str, Any]] | None = None
    validity_date: date | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    submitted_at: datetime
    is_best_offer: bool
    source_document_id: uuid.UUID | None = None
    supplier_legal_name: str | None = None
    supplier_country: str | None = None


class PaginatedRFxResponses(BaseModel):
    items: list[RFxResponseOut]
    total: int
    limit: int
    offset: int


# ── RFx Event Schemas ────────────────────────────────────────────────────────

class RFxEventCreate(BaseModel):
    rfx_type: Literal["rfi", "rfq", "rfp", "rft"] = "rfq"
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    material_request_id: uuid.UUID | None = None
    category: str | None = None
    evaluation_criteria: list[EvaluationCriterion] = Field(
        default_factory=lambda: [
            EvaluationCriterion(criterion="Price", weight=40.0, description="Cost competitiveness"),
            EvaluationCriterion(criterion="Quality", weight=25.0, description="Product quality and compliance"),
            EvaluationCriterion(criterion="Delivery", weight=20.0, description="Lead time and fulfillment speed"),
            EvaluationCriterion(criterion="Risk", weight=15.0, description="Supplier risk assessment rating"),
        ]
    )
    submission_deadline: datetime | None = None
    supplier_ids: list[uuid.UUID] = Field(default_factory=list)


class RFxEventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    rfx_type: Literal["rfi", "rfq", "rfp", "rft"] | None = None
    category: str | None = None
    evaluation_criteria: list[EvaluationCriterion] | None = None
    submission_deadline: datetime | None = None


class RFxEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    rfx_number: str
    rfx_type: str
    title: str
    description: str | None = None
    status: str
    material_request_id: uuid.UUID | None = None
    category: str | None = None
    evaluation_criteria: list[dict[str, Any]]
    published_at: datetime | None = None
    submission_deadline: datetime | None = None
    awarded_at: datetime | None = None
    awarded_supplier_id: uuid.UUID | None = None
    awarded_supplier_name: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    invitations: list[RFxInvitationOut] = Field(default_factory=list)
    responses: list[RFxResponseOut] = Field(default_factory=list)
    total_invitations: int = 0
    total_responses: int = 0


class PaginatedRFxEvents(BaseModel):
    items: list[RFxEventOut]
    total: int
    limit: int
    offset: int


# ── Bid Comparison & Award Schemas ───────────────────────────────────────────

class BidComparisonItem(BaseModel):
    response_id: uuid.UUID
    response_number: str
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_country: str | None = None
    total_amount: float
    currency: str
    average_lead_time_days: int | None = None
    line_items: list[dict[str, Any]]
    criteria_scores: dict[str, float]
    normalized_price_score: float
    composite_score: float
    is_best_offer: bool
    price_rank: int
    overall_rank: int
    payment_terms: str | None = None
    delivery_terms: str | None = None


class BidComparisonResult(BaseModel):
    rfx_id: uuid.UUID
    rfx_number: str
    rfx_type: str
    title: str
    status: str
    criteria: list[dict[str, Any]]
    bids: list[BidComparisonItem]
    recommended_response_id: uuid.UUID | None = None
    recommended_supplier_id: uuid.UUID | None = None
    recommended_supplier_name: str | None = None
    recommendation_summary: str | None = None


class AwardRFxRequest(BaseModel):
    response_id: uuid.UUID
    notes: str | None = None
