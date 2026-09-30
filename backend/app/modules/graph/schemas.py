"""
app/modules/graph/schemas.py — Pydantic request/response schemas for suppliers & relationships.

Per arch §G.3 & §12.3: supplier_relationships is the ONLY table carrying org_id
on the graph, encoding who-buys-from-whom.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.pagination import PaginationMeta
from app.modules.companies.schemas import CompanySummaryOut

# ── Suppliers (direct supply edges to tenant org) ───────────────────────────

class SupplierOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    company_id: uuid.UUID
    company: CompanySummaryOut
    relationship_type: str
    tier: int | None = 1
    criticality: int | None = None
    annual_spend_usd: float | None = None
    category: str | None = None
    single_source: bool = False
    lead_time_days: int | None = None
    confidence: float = 1.0
    source: str = "user_declared"
    valid_from: date
    valid_to: date | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierCreate(BaseModel):
    # Either company_id of existing canonical company OR new company details
    company_id: uuid.UUID | None = None
    legal_name: str | None = Field(None, min_length=1, max_length=500)
    country: str | None = Field(None, min_length=2, max_length=2)
    primary_domain: str | None = Field(None, max_length=255)

    tier: int = Field(default=1, ge=1, le=10)
    criticality: int = Field(default=3, ge=1, le=5)
    annual_spend_usd: float | None = Field(default=None, ge=0)
    category: str | None = None
    single_source: bool = False
    lead_time_days: int | None = Field(default=None, ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "user_declared"

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else v

    @model_validator(mode="after")
    def _check_company_spec(self) -> SupplierCreate:
        if not self.company_id and not self.legal_name:
            raise ValueError("Either company_id or legal_name must be provided")
        return self


class SupplierUpdate(BaseModel):
    criticality: int | None = Field(default=None, ge=1, le=5)
    annual_spend_usd: float | None = Field(default=None, ge=0)
    category: str | None = None
    tier: int | None = Field(default=None, ge=1, le=10)
    single_source: bool | None = None
    lead_time_days: int | None = Field(default=None, ge=0)


class PaginatedSuppliers(BaseModel):
    data: list[SupplierOut]
    pagination: PaginationMeta


# ── Generic Graph Relationships ─────────────────────────────────────────────

class RelationshipOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    from_company_id: uuid.UUID
    from_company: CompanySummaryOut | None = None
    to_company_id: uuid.UUID | None = None
    to_company: CompanySummaryOut | None = None
    to_org_id: uuid.UUID | None = None
    relationship_type: str
    tier: int | None = None
    criticality: int | None = None
    annual_spend_usd: float | None = None
    category: str | None = None
    single_source: bool = False
    lead_time_days: int | None = None
    confidence: float = 1.0
    source: str = "user_declared"
    valid_from: date
    valid_to: date | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RelationshipCreate(BaseModel):
    from_company_id: uuid.UUID
    to_company_id: uuid.UUID | None = None
    to_org_id: uuid.UUID | None = None
    relationship_type: str = Field(
        default="supplies_to",
        description="supplies_to | sub_supplies_to | owned_by | located_in",
    )
    tier: int | None = Field(default=None, ge=1, le=10)
    criticality: int | None = Field(default=None, ge=1, le=5)
    annual_spend_usd: float | None = Field(default=None, ge=0)
    category: str | None = None
    single_source: bool = False
    lead_time_days: int | None = Field(default=None, ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = "user_declared"

    @model_validator(mode="after")
    def _check_targets(self) -> RelationshipCreate:
        if not self.to_company_id and not self.to_org_id:
            raise ValueError("Either to_company_id or to_org_id must be provided")
        return self


class RelationshipUpdate(BaseModel):
    relationship_type: str | None = None
    tier: int | None = Field(default=None, ge=1, le=10)
    criticality: int | None = Field(default=None, ge=1, le=5)
    annual_spend_usd: float | None = Field(default=None, ge=0)
    category: str | None = None
    single_source: bool | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class PaginatedRelationships(BaseModel):
    data: list[RelationshipOut]
    pagination: PaginationMeta
