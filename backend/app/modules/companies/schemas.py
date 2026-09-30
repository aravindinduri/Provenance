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
    created_at: datetime
    updated_at: datetime

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
