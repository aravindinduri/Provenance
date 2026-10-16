"""
app/modules/purchase_orders/schemas.py — Pydantic schemas for Purchase Order lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class POLineItemCreate(BaseModel):
    item_id: uuid.UUID | None = None
    item_code: str | None = None
    description: str
    quantity: float = Field(..., gt=0)
    unit_of_measure: str | None = "each"
    unit_price: float = Field(..., ge=0)
    total_price: float | None = None


class POLineItemOut(BaseModel):
    po_line_index: int = 0
    item_id: str | None = None
    item_code: str | None = None
    description: str
    quantity: float
    unit_of_measure: str | None = "each"
    unit_price: float
    total_price: float
    qty_received: float = 0.0
    qty_rejected: float = 0.0


class DeliveryAddress(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class PurchaseOrderCreate(BaseModel):
    company_id: uuid.UUID
    contract_id: uuid.UUID | None = None
    material_request_id: uuid.UUID | None = None
    rfx_event_id: uuid.UUID | None = None
    rfx_response_id: uuid.UUID | None = None
    order_date: date | None = None
    expected_delivery_date: date | None = None
    currency: str = "USD"
    line_items: list[POLineItemCreate] = Field(..., min_length=1)
    delivery_address: DeliveryAddress | dict[str, Any] | None = None
    payment_terms: str | None = "Net 30"
    delivery_terms: str | None = "FOB Destination"
    notes: str | None = None


class PurchaseOrderUpdate(BaseModel):
    company_id: uuid.UUID | None = None
    order_date: date | None = None
    expected_delivery_date: date | None = None
    currency: str | None = None
    line_items: list[POLineItemCreate] | None = None
    delivery_address: DeliveryAddress | dict[str, Any] | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    notes: str | None = None


class GRNSummaryOut(BaseModel):
    id: uuid.UUID
    grn_number: str
    received_date: date
    received_by: str | None
    status: str
    delivery_note_ref: str | None
    carrier: str | None
    line_items: list[dict[str, Any]] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class PurchaseOrderOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    po_number: str
    company_id: uuid.UUID | None
    company_name: str | None = None
    contract_id: uuid.UUID | None = None
    material_request_id: uuid.UUID | None = None
    rfx_event_id: uuid.UUID | None = None
    rfx_response_id: uuid.UUID | None = None
    order_date: date | None = None
    expected_delivery_date: date | None = None
    total_amount: float
    currency: str
    line_items: list[dict[str, Any]]
    status: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    delivery_address: dict[str, Any] | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    notes: str | None = None
    created_at: datetime
    receipt_count: int = 0
    receipts: list[GRNSummaryOut] = []

    model_config = {"from_attributes": True}


class PaginatedPurchaseOrders(BaseModel):
    items: list[PurchaseOrderOut]
    total: int
    limit: int
    offset: int
