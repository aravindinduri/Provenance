"""
/v1/invoices — Phase 4 Purchase Invoice & 3-Way Matching API router.

GET   /invoices              List invoices with filters & pagination
GET   /invoices/stats        Live dynamically computed stats
POST  /invoices              Create / ingest supplier invoice
GET   /invoices/{id}         Get invoice details with PO/GRN lines
POST  /invoices/{id}/match   Trigger deterministic 2-way or 3-way match
POST  /invoices/{id}/approve Override / approve invoice
POST  /invoices/{id}/pay     Record supplier payment
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.invoices.matching_engine import MatchTolerances
from app.modules.invoices.schemas import (
    InvoiceCreate,
    InvoiceMatchResult,
    InvoiceOut,
    InvoicePayRequest,
    InvoiceStatsOut,
    PaginatedInvoices,
)
from app.modules.invoices.service import (
    InvalidInvoiceState,
    InvoiceNotFound,
    InvoiceService,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _svc(db: AsyncSession = Depends(get_db)) -> InvoiceService:
    return InvoiceService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedInvoices)
async def list_invoices(
    po_id: uuid.UUID | None = Query(None),
    company_id: uuid.UUID | None = Query(None),
    match_status: str | None = Query(None),
    payment_status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> PaginatedInvoices:
    return await svc.list_invoices(
        _org_id(current_user),
        po_id=po_id,
        company_id=company_id,
        match_status=match_status,
        payment_status=payment_status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=InvoiceStatsOut)
async def get_invoice_stats(
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> InvoiceStatsOut:
    return await svc.get_stats(_org_id(current_user))


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> InvoiceOut:
    try:
        return await svc.create_invoice(
            _org_id(current_user), data, user_id=current_user.user_id
        )
    except InvalidInvoiceState as exc:
        raise bad_request(str(exc))


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> InvoiceOut:
    try:
        return await svc.get_invoice(invoice_id, _org_id(current_user))
    except InvoiceNotFound as exc:
        raise not_found(str(exc))


@router.post("/{invoice_id}/match", response_model=InvoiceMatchResult)
async def match_invoice(
    invoice_id: uuid.UUID,
    price_tolerance_pct: float = Query(2.0, ge=0.0, le=50.0),
    qty_tolerance_pct: float = Query(5.0, ge=0.0, le=50.0),
    amount_tolerance_abs: float = Query(500.0, ge=0.0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> InvoiceMatchResult:
    try:
        tolerances = MatchTolerances(
            price_tolerance_pct=price_tolerance_pct,
            qty_tolerance_pct=qty_tolerance_pct,
            amount_tolerance_abs=amount_tolerance_abs,
        )
        return await svc.match_invoice(
            invoice_id,
            _org_id(current_user),
            user_id=current_user.user_id,
            tolerances=tolerances,
        )
    except InvoiceNotFound as exc:
        raise not_found(str(exc))


@router.post("/{invoice_id}/approve", response_model=InvoiceOut)
async def approve_invoice(
    invoice_id: uuid.UUID,
    notes: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> InvoiceOut:
    try:
        return await svc.approve_invoice(
            invoice_id,
            _org_id(current_user),
            user_id=current_user.user_id,
            notes=notes,
        )
    except InvoiceNotFound as exc:
        raise not_found(str(exc))


@router.post("/{invoice_id}/pay", response_model=InvoiceOut)
async def pay_invoice(
    invoice_id: uuid.UUID,
    data: InvoicePayRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: InvoiceService = Depends(_svc),
) -> InvoiceOut:
    try:
        return await svc.record_payment(
            invoice_id,
            _org_id(current_user),
            data,
            user_id=current_user.user_id,
        )
    except InvoiceNotFound as exc:
        raise not_found(str(exc))
