"""
/v1/rfx — RFx Sourcing Event lifecycle

GET    /rfx                  list sourcing events
POST   /rfx                  create draft RFx
GET    /rfx/{id}             get single RFx with invitations and responses
PATCH  /rfx/{id}             update draft RFx
POST   /rfx/{id}/publish     publish RFx
POST   /rfx/{id}/close       close RFx to submissions
POST   /rfx/{id}/cancel      cancel RFx
POST   /rfx/{id}/invite      invite suppliers
GET    /rfx/{id}/compare     bid comparison matrix with deterministic scoring
POST   /rfx/{id}/award       award RFx to winning response
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.rfx.schemas import (
    AwardRFxRequest,
    BidComparisonResult,
    InviteSuppliersRequest,
    PaginatedRFxEvents,
    RFxEventCreate,
    RFxEventOut,
    RFxEventUpdate,
    RFxInvitationOut,
)
from app.modules.rfx.service import (
    InvalidRFxStatusTransition,
    RFxNotFound,
    RFxResponseNotFound,
    RFxService,
)

router = APIRouter(prefix="/rfx", tags=["rfx"])


def _svc(db: AsyncSession = Depends(get_db)) -> RFxService:
    return RFxService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedRFxEvents)
async def list_rfx_events(
    status_filter: str | None = Query(None, alias="status"),
    rfx_type: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> PaginatedRFxEvents:
    return await svc.list_rfx(
        _org_id(current_user),
        status=status_filter,
        rfx_type=rfx_type,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=RFxEventOut, status_code=status.HTTP_201_CREATED)
async def create_rfx_event(
    data: RFxEventCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    rfx = await svc.create_rfx(_org_id(current_user), data, user_id=current_user.user_id)
    return svc._format_rfx_out(rfx)


@router.get("/{rfx_id}", response_model=RFxEventOut)
async def get_rfx_event(
    rfx_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    try:
        rfx = await svc.get_rfx(rfx_id, _org_id(current_user))
    except RFxNotFound:
        raise not_found("RFx event not found")
    return svc._format_rfx_out(rfx)


@router.patch("/{rfx_id}", response_model=RFxEventOut)
async def update_rfx_event(
    rfx_id: uuid.UUID,
    data: RFxEventUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    try:
        rfx = await svc.update_rfx(rfx_id, _org_id(current_user), data, user_id=current_user.user_id)
    except RFxNotFound:
        raise not_found("RFx event not found")
    except InvalidRFxStatusTransition as exc:
        raise bad_request(str(exc))
    return svc._format_rfx_out(rfx)


@router.post("/{rfx_id}/publish", response_model=RFxEventOut)
async def publish_rfx_event(
    rfx_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    try:
        rfx = await svc.publish_rfx(rfx_id, _org_id(current_user), user_id=current_user.user_id)
    except RFxNotFound:
        raise not_found("RFx event not found")
    except InvalidRFxStatusTransition as exc:
        raise bad_request(str(exc))
    return svc._format_rfx_out(rfx)


@router.post("/{rfx_id}/close", response_model=RFxEventOut)
async def close_rfx_event(
    rfx_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    try:
        rfx = await svc.close_rfx(rfx_id, _org_id(current_user), user_id=current_user.user_id)
    except RFxNotFound:
        raise not_found("RFx event not found")
    except InvalidRFxStatusTransition as exc:
        raise bad_request(str(exc))
    return svc._format_rfx_out(rfx)


@router.post("/{rfx_id}/cancel", response_model=RFxEventOut)
async def cancel_rfx_event(
    rfx_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    try:
        rfx = await svc.cancel_rfx(rfx_id, _org_id(current_user), user_id=current_user.user_id)
    except RFxNotFound:
        raise not_found("RFx event not found")
    except InvalidRFxStatusTransition as exc:
        raise bad_request(str(exc))
    return svc._format_rfx_out(rfx)


@router.post("/{rfx_id}/invite", response_model=list[RFxInvitationOut])
async def invite_suppliers(
    rfx_id: uuid.UUID,
    data: InviteSuppliersRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> list[RFxInvitationOut]:
    try:
        invs = await svc.invite_suppliers(
            rfx_id, _org_id(current_user), data.supplier_ids, user_id=current_user.user_id
        )
    except RFxNotFound:
        raise not_found("RFx event not found")
    return [
        RFxInvitationOut(
            id=inv.id,
            rfx_event_id=inv.rfx_event_id,
            supplier_id=inv.supplier_id,
            status=inv.status,
            invited_at=inv.invited_at,
            responded_at=inv.responded_at,
            supplier_legal_name=inv.supplier.legal_name if inv.supplier else None,
            supplier_country=inv.supplier.country if inv.supplier else None,
        )
        for inv in invs
    ]


@router.get("/{rfx_id}/compare", response_model=BidComparisonResult)
async def compare_rfx_bids(
    rfx_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> BidComparisonResult:
    try:
        return await svc.compare_bids(rfx_id, _org_id(current_user))
    except RFxNotFound:
        raise not_found("RFx event not found")


@router.post("/{rfx_id}/award", response_model=RFxEventOut)
async def award_rfx_event(
    rfx_id: uuid.UUID,
    data: AwardRFxRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: RFxService = Depends(_svc),
) -> RFxEventOut:
    try:
        rfx = await svc.award_rfx(
            rfx_id,
            _org_id(current_user),
            data.response_id,
            user_id=current_user.user_id,
            notes=data.notes,
        )
    except RFxNotFound:
        raise not_found("RFx event not found")
    except RFxResponseNotFound:
        raise not_found("Quotation response not found")
    except (InvalidRFxStatusTransition, ValueError) as exc:
        raise bad_request(str(exc))
    return svc._format_rfx_out(rfx)
