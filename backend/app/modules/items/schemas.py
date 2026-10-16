"""
app/modules/items/schemas.py — Pydantic schemas for the items module.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ItemCreate(BaseModel):
    item_code: str
    name: str
    description: str | None = None
    category: str | None = None
    unit_of_measure: str | None = None
    default_unit_price: float | None = None
    currency: str | None = None
    preferred_supplier_id: uuid.UUID | None = None
    lead_time_days: int | None = None
    min_order_qty: float | None = None
    is_active: bool = True
    metadata: dict[str, Any] | None = None

    @field_validator("preferred_supplier_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Any:
        if v == "" or v is None:
            return None
        return v


class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    unit_of_measure: str | None = None
    default_unit_price: float | None = None
    currency: str | None = None
    preferred_supplier_id: uuid.UUID | None = None
    lead_time_days: int | None = None
    min_order_qty: float | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("preferred_supplier_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Any:
        if v == "" or v is None:
            return None
        return v


class ItemOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    item_code: str
    name: str
    description: str | None = None
    category: str | None = None
    unit_of_measure: str | None = None
    default_unit_price: float | None = None
    currency: str | None = None
    preferred_supplier_id: uuid.UUID | None = None
    lead_time_days: int | None = None
    min_order_qty: float | None = None
    is_active: bool
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class PaginatedItems(BaseModel):
    items: list[ItemOut]
    total: int
    limit: int
    offset: int
