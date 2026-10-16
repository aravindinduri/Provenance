"""
/v1/supplier-quotations — Supplier Quotations / Proposals lifecycle

GET    /supplier-quotations                list quotations
POST   /supplier-quotations                submit quotation/proposal
GET    /supplier-quotations/{id}           get single quotation
PATCH  /supplier-quotations/{id}/evaluate  evaluate / score quotation criteria
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import not_found
from app.db.session import get_db
from app.modules.rfx.schemas import (
    PaginatedRFxResponses,
    RFxResponseCreate,
    RFxResponseEvaluateRequest,
    RFxResponseOut,
)
from app.modules.rfx.service import (
    RFxNotFound,
    RFxResponseNotFound,
    RFxService,
)

router = APIRouter(prefix="/supplier-quotations", tags=["supplier-quotations"])


def _svc(db: AsyncSession = Depends(get_db)) -> RFxService:
    return RFxService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedRFxResponses)
async def list_supplier_quotations(
    rfx_event_id: uuid.UUID | None = Query(None),
    supplier_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> PaginatedRFxResponses:
    return await svc.list_responses(
        _org_id(current_user),
        rfx_event_id=rfx_event_id,
        supplier_id=supplier_id,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=RFxResponseOut, status_code=status.HTTP_201_CREATED)
async def create_supplier_quotation(
    data: RFxResponseCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxResponseOut:
    try:
        resp = await svc.create_response(_org_id(current_user), data, user_id=current_user.user_id)
    except RFxNotFound:
        raise not_found("RFx event not found")
    return svc._format_response_out(resp)


@router.get("/{response_id}", response_model=RFxResponseOut)
async def get_supplier_quotation(
    response_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxResponseOut:
    try:
        resp = await svc.get_response(response_id, _org_id(current_user))
    except RFxResponseNotFound:
        raise not_found("Quotation response not found")
    return svc._format_response_out(resp)


@router.patch("/{response_id}/evaluate", response_model=RFxResponseOut)
async def evaluate_supplier_quotation(
    response_id: uuid.UUID,
    data: RFxResponseEvaluateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxResponseOut:
    try:
        resp = await svc.evaluate_response(
            response_id, _org_id(current_user), data, user_id=current_user.user_id
        )
    except RFxResponseNotFound:
        raise not_found("Quotation response not found")
    return svc._format_response_out(resp)
