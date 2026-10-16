"""
app/modules/invoices/schemas.py — Pydantic schemas for Invoices and 3-Way Matching.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Line Items ────────────────────────────────────────────────────────────────

class InvoiceLineItemInput(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    total_amount: float | None = None
    unit_of_measure: str = Field("each", max_length=20)
    item_id: uuid.UUID | None = None
    item_code: str | None = None
    po_line_index: int = Field(0, ge=0)


class InvoiceLineItemOut(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total_amount: float
    unit_of_measure: str = "each"
    item_id: str | None = None
    item_code: str | None = None
    po_line_index: int = 0


# ── Matching Details ──────────────────────────────────────────────────────────

class MatchExceptionItem(BaseModel):
    code: str  # price_variance, quantity_mismatch, missing_po, missing_goods_receipt, total_amount_variance, unapproved_po
    severity: Literal["critical", "warning"] = "warning"
    message: str
    line_index: int | None = None
    expected: float | str | None = None
    actual: float | str | None = None
    variance_pct: float | None = None


class LineMatchDetail(BaseModel):
    po_line_index: int
    item_code: str | None = None
    description: str
    po_quantity: float
    grn_quantity: float | None = None
    invoice_quantity: float
    po_unit_price: float
    invoice_unit_price: float
    price_variance_pct: float
    qty_delta: float
    status: Literal["matched", "variance", "missing"]
    notes: str | None = None


class InvoiceMatchResult(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    match_type: Literal["2way", "3way", "unmatched"]
    match_status: Literal["matched_2way", "matched_3way", "exception"]
    po_id: uuid.UUID | None = None
    po_number: str | None = None
    goods_receipt_id: uuid.UUID | None = None
    grn_number: str | None = None
    supplier_name: str | None = None
    within_tolerance: bool
    summary: str
    line_matches: list[LineMatchDetail] = []
    exceptions: list[MatchExceptionItem] = []
    tolerances_used: dict[str, float] = {}


# ── Invoice Create / Update ───────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    company_id: uuid.UUID | None = None
    supplier_name: str | None = None
    po_id: uuid.UUID | None = None
    goods_receipt_id: uuid.UUID | None = None
    invoice_number: str | None = None  # Auto-generated if not provided
    invoice_date: date | None = None
    due_date: date | None = None
    amount: float | None = None  # Computed from lines if omitted
    currency: str = Field("USD", min_length=3, max_length=3)
    category: str | None = None
    line_items: list[InvoiceLineItemInput] = []
    notes: str | None = None
    auto_match: bool = True


class InvoiceUpdate(BaseModel):
    invoice_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    payment_status: Literal["unpaid", "partially_paid", "paid", "overdue", "disputed"] | None = None


class InvoicePayRequest(BaseModel):
    amount: float | None = None  # Full remaining amount if omitted
    payment_reference: str | None = None
    payment_method: str = "wire_transfer"
    notes: str | None = None


# ── Invoice Output ────────────────────────────────────────────────────────────

class InvoiceOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    invoice_number: str
    company_id: uuid.UUID | None = None
    supplier_name: str | None = None
    po_id: uuid.UUID | None = None
    po_number: str | None = None
    goods_receipt_id: uuid.UUID | None = None
    grn_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    amount: float
    currency: str
    category: str | None = None
    payment_status: str  # unpaid, partially_paid, paid, overdue, disputed
    match_status: str    # unmatched, matched_2way, matched_3way, exception
    match_exceptions: list[dict[str, Any]] = []
    approved_by: str | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    line_items: list[dict[str, Any]] = []
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedInvoices(BaseModel):
    items: list[InvoiceOut]
    total: int
    limit: int
    offset: int


class InvoiceStatsOut(BaseModel):
    total_count: int
    total_amount: float
    matched_3way_count: int
    matched_2way_count: int
    exception_count: int
    unmatched_count: int
    paid_count: int
    unpaid_count: int
    paid_amount: float
