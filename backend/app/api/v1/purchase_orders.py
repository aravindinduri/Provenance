"""
/v1/purchase-orders — Purchase Order lifecycle and operations.

GET    /purchase-orders                  list purchase orders with filters
POST   /purchase-orders                  create draft PO
GET    /purchase-orders/{id}             get single PO with line items & receipt summaries
PATCH  /purchase-orders/{id}             update draft PO
POST   /purchase-orders/{id}/submit      submit PO for DoA approval
POST   /purchase-orders/{id}/approve     approve PO
POST   /purchase-orders/{id}/send        mark dispatched to vendor
POST   /purchase-orders/{id}/acknowledge mark acknowledged by vendor
POST   /purchase-orders/{id}/close       close completed PO
POST   /purchase-orders/{id}/cancel      cancel PO
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.purchase_orders.schemas import (
    PaginatedPurchaseOrders,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    PurchaseOrderUpdate,
)
from app.modules.purchase_orders.service import (
    InvalidPOStatusTransition,
    PONotFound,
    PurchaseOrderService,
)

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


def _svc(db: AsyncSession = Depends(get_db)) -> PurchaseOrderService:
    return PurchaseOrderService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


class ActionNotesRequest(BaseModel):
    notes: str | None = None
    reason: str | None = None


@router.get("", response_model=PaginatedPurchaseOrders)
async def list_purchase_orders(
    status_filter: str | None = Query(None, alias="status"),
    company_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PaginatedPurchaseOrders:
    return await svc.list_pos(
        _org_id(current_user),
        status=status_filter,
        company_id=company_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: PurchaseOrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    return await svc.create_po(_org_id(current_user), data, user_id=current_user.user_id)


@router.get("/{po_id}", response_model=PurchaseOrderOut)
async def get_purchase_order(
    po_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        return await svc.get_po(po_id, _org_id(current_user))
    except PONotFound as exc:
        raise not_found(str(exc))


@router.patch("/{po_id}", response_model=PurchaseOrderOut)
async def update_purchase_order(
    po_id: uuid.UUID,
    data: PurchaseOrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        return await svc.update_po(
            po_id, _org_id(current_user), data, user_id=current_user.user_id
        )
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{po_id}/submit", response_model=PurchaseOrderOut)
async def submit_purchase_order(
    po_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        return await svc.submit_po(po_id, _org_id(current_user), user_id=current_user.user_id)
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{po_id}/approve", response_model=PurchaseOrderOut)
async def approve_purchase_order(
    po_id: uuid.UUID,
    body: ActionNotesRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        comments = body.notes if body else None
        return await svc.approve_po(
            po_id, _org_id(current_user), user_id=current_user.user_id, comments=comments
        )
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{po_id}/send", response_model=PurchaseOrderOut)
async def send_purchase_order(
    po_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        return await svc.send_po(po_id, _org_id(current_user), user_id=current_user.user_id)
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{po_id}/acknowledge", response_model=PurchaseOrderOut)
async def acknowledge_purchase_order(
    po_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        return await svc.acknowledge_po(po_id, _org_id(current_user), user_id=current_user.user_id)
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{po_id}/close", response_model=PurchaseOrderOut)
async def close_purchase_order(
    po_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        return await svc.close_po(po_id, _org_id(current_user), user_id=current_user.user_id)
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{po_id}/cancel", response_model=PurchaseOrderOut)
async def cancel_purchase_order(
    po_id: uuid.UUID,
    body: ActionNotesRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    svc: PurchaseOrderService = Depends(_svc),
) -> PurchaseOrderOut:
    try:
        reason = body.reason if body else None
        return await svc.cancel_po(
            po_id, _org_id(current_user), user_id=current_user.user_id, reason=reason
        )
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidPOStatusTransition as exc:
        raise bad_request(str(exc))
