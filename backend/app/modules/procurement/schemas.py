"""
app/modules/procurement/schemas.py — Pydantic schemas for material requests.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

MRStatus = Literal[
    "draft", "pending_approval", "approved", "ordered", "partially_ordered", "cancelled"
]
Priority = Literal["low", "medium", "high", "critical"]


def _parse_flexible_date(v: Any) -> Any:
    if v == "" or v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue
    return v


class MRLineItemCreate(BaseModel):
    item_id: uuid.UUID | None = None
    description: str
    quantity: float
    unit_of_measure: str | None = None
    estimated_unit_price: float | None = None
    currency: str | None = None
    preferred_supplier_id: uuid.UUID | None = None

    @field_validator("item_id", "preferred_supplier_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Any:
        if v == "" or v is None:
            return None
        return v


class MRLineItemOut(BaseModel):
    id: uuid.UUID
    material_request_id: uuid.UUID
    item_id: uuid.UUID | None = None
    description: str
    quantity: float
    unit_of_measure: str | None = None
    estimated_unit_price: float | None = None
    currency: str | None = None
    preferred_supplier_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class MaterialRequestCreate(BaseModel):
    title: str
    required_by_date: date | None = None
    priority: Priority = "medium"
    department: str | None = None
    justification: str | None = None
    currency: str | None = None
    line_items: list[MRLineItemCreate] = []

    @field_validator("required_by_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> Any:
        return _parse_flexible_date(v)

    @field_validator("priority", mode="before")
    @classmethod
    def coerce_priority(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("low", "medium", "high", "critical"):
                return v_lower
        return v


class MaterialRequestUpdate(BaseModel):
    title: str | None = None
    required_by_date: date | None = None
    priority: Priority | None = None
    department: str | None = None
    justification: str | None = None
    currency: str | None = None

    @field_validator("required_by_date", mode="before")
    @classmethod
    def coerce_date(cls, v: Any) -> Any:
        return _parse_flexible_date(v)

    @field_validator("priority", mode="before")
    @classmethod
    def coerce_priority(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("low", "medium", "high", "critical"):
                return v_lower
        return v


class MaterialRequestOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    mr_number: str
    title: str
    status: str
    requested_by: str | None = None
    required_by_date: date | None = None
    priority: str | None = None
    department: str | None = None
    justification: str | None = None
    total_estimated_amount: float | None = None
    currency: str | None = None
    line_items: list[MRLineItemOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedMaterialRequests(BaseModel):
    items: list[MaterialRequestOut]
    total: int
    limit: int
    offset: int


class MRSubmitAction(BaseModel):
    """Submit a draft MR for approval."""
    pass


class MRApproveRejectAction(BaseModel):
    action: Literal["approve", "reject"]
    comments: str | None = None
