"""
app/modules/goods_receipts/schemas.py — Pydantic schemas for Goods Receipt Notes (GRN).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class GRNLineItemInput(BaseModel):
    po_line_index: int = Field(..., ge=0)
    item_id: uuid.UUID | None = None
    item_code: str | None = None
    description: str
    qty_received: float = Field(..., ge=0)
    qty_rejected: float = Field(default=0.0, ge=0)
    unit_of_measure: str | None = "each"
    inspection_notes: str | None = None


class GoodsReceiptCreate(BaseModel):
    purchase_order_id: uuid.UUID
    received_date: date | None = None
    received_by: str | None = None
    delivery_note_ref: str | None = None
    carrier: str | None = None
    notes: str | None = None
    line_items: list[GRNLineItemInput] = Field(..., min_length=1)
    auto_confirm: bool = False


class GoodsReceiptUpdate(BaseModel):
    received_date: date | None = None
    received_by: str | None = None
    delivery_note_ref: str | None = None
    carrier: str | None = None
    notes: str | None = None
    line_items: list[GRNLineItemInput] | None = None


class GoodsReceiptOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    grn_number: str
    purchase_order_id: uuid.UUID
    po_number: str | None = None
    supplier_name: str | None = None
    received_date: date
    received_by: str | None = None
    status: str
    line_items: list[dict[str, Any]]
    delivery_note_ref: str | None = None
    carrier: str | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedGoodsReceipts(BaseModel):
    items: list[GoodsReceiptOut]
    total: int
    limit: int
    offset: int
