"""
app/modules/companies/schemas.py — Pydantic schemas for the companies module.

Exposes canonical company profiles, search results, identifiers, and locations.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.pagination import PaginationMeta

# ── Identifiers & Aliases ───────────────────────────────────────────────────

class CompanyIdentifierOut(BaseModel):
    id: uuid.UUID
    identifier_type: str
    identifier_value: str
    issuing_country: str | None = None
    source: str | None = None
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class CompanyAliasOut(BaseModel):
    id: uuid.UUID
    alias: str
    alias_norm: str
    alias_type: str | None = None
    source: str | None = None
    confidence: float | None = None

    model_config = {"from_attributes": True}


# ── Locations ────────────────────────────────────────────────────────────────

class LocationOut(BaseModel):
    id: uuid.UUID
    country: str
    region: str | None = None
    city: str | None = None
    lat: float | None = None
    lon: float | None = None
    geohash: str | None = None

    model_config = {"from_attributes": True}


class CompanyLocationOut(BaseModel):
    id: uuid.UUID
    site_type: str | None = None
    is_primary: bool = False
    source: str | None = None
    confidence: float = 1.0
    valid_from: date | None = None
    valid_to: date | None = None
    location: LocationOut

    model_config = {"from_attributes": True}


# ── Company Out ──────────────────────────────────────────────────────────────

class CompanySummaryOut(BaseModel):
    id: uuid.UUID
    legal_name: str
    name_norm: str
    country: str | None = None
    jurisdiction: str | None = None
    legal_form: str | None = None
    entity_status: str | None = None
    primary_domain: str | None = None
    industry_codes: list[str] = Field(default_factory=list)
    data_source: str | None = None
    confidence: float = 1.0
    is_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("industry_codes", mode="before")
    @classmethod
    def _parse_industry_codes(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return []

    model_config = {"from_attributes": True}


class CompanyDetailOut(CompanySummaryOut):
    registered_address: dict[str, Any] | None = None
    hq_address: dict[str, Any] | None = None
    last_enriched_at: datetime | None = None
    identifiers: list[CompanyIdentifierOut] = Field(default_factory=list)
    aliases: list[CompanyAliasOut] = Field(default_factory=list)
    locations: list[CompanyLocationOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CompanyCreate(BaseModel):
    legal_name: str = Field(min_length=1, max_length=500)
    country: str | None = Field(None, min_length=2, max_length=2)
    jurisdiction: str | None = Field(None, max_length=100)
    primary_domain: str | None = Field(None, max_length=255)
    industry_codes: list[str] = Field(default_factory=list)

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class PaginatedCompanies(BaseModel):
    data: list[CompanySummaryOut]
    pagination: PaginationMeta


# ── Entity Resolution & Review Queue (Phase 9) ──────────────────────────────

class CandidateMatchOut(BaseModel):
    company_id: uuid.UUID
    legal_name: str
    country: str | None = None
    primary_domain: str | None = None
    similarity: float
    match_reason: str | None = None


class EntityResolveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    country: str | None = Field(None, min_length=2, max_length=2)
    domain: str | None = Field(None, max_length=255)
    identifiers: dict[str, str] | None = None
    address: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    auto_review: bool = True

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class EntityResolveResponse(BaseModel):
    matched: bool
    stage: int
    match_method: str  # identifier|domain|exact_name_country|exact_name|fuzzy|ai|unresolved
    confidence: float
    company_id: uuid.UUID | None = None
    company: CompanySummaryOut | None = None
    review_id: uuid.UUID | None = None
    reasoning: str | None = None
    candidates: list[CandidateMatchOut] = Field(default_factory=list)


class Stage6AdjudicationOut(BaseModel):
    """Structured output expected from Stage 6 AI adjudication agent."""
    decision: str = Field(description="'match', 'no_match', or 'uncertain'")
    company_id: str | None = Field(None, description="UUID of matched company from candidate list, or null")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Explanation of the adjudication decision")
    evidence_fields: list[str] = Field(default_factory=list, description="Fields that supported the match")


class EntityResolutionReviewOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID | None = None
    raw_name: str
    context: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    suggested_company_id: uuid.UUID | None = None
    suggested_company: CompanySummaryOut | None = None
    ai_confidence: float | None = None
    ai_reasoning: str | None = None
    status: str  # pending|resolved|rejected|new_entity
    resolved_company_id: uuid.UUID | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EntityReviewResolveRequest(BaseModel):
    action: str = Field(description="'match', 'reject', or 'create_new'")
    company_id: uuid.UUID | None = None
    legal_name: str | None = None
    country: str | None = None
    notes: str | None = None


class PaginatedEntityReviews(BaseModel):
    data: list[EntityResolutionReviewOut]
    pagination: PaginationMeta

