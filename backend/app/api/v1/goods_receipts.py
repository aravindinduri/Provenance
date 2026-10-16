"""
/v1/goods-receipts — Goods Receipt Note (GRN) operations and fulfillment tracking.

GET    /goods-receipts              list goods receipts with filters
POST   /goods-receipts              record a goods receipt note against a PO
GET    /goods-receipts/{id}         get goods receipt details
POST   /goods-receipts/{id}/confirm confirm goods receipt and update PO receipt status
POST   /goods-receipts/{id}/cancel  cancel draft goods receipt
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.goods_receipts.schemas import (
    GoodsReceiptCreate,
    GoodsReceiptOut,
    PaginatedGoodsReceipts,
)
from app.modules.goods_receipts.service import (
    GoodsReceiptNotFound,
    GoodsReceiptService,
    InvalidGRNStatusTransition,
)
from app.modules.purchase_orders.service import PONotFound

router = APIRouter(prefix="/goods-receipts", tags=["goods-receipts"])


def _svc(db: AsyncSession = Depends(get_db)) -> GoodsReceiptService:
    return GoodsReceiptService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedGoodsReceipts)
async def list_goods_receipts(
    purchase_order_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: GoodsReceiptService = Depends(_svc),
) -> PaginatedGoodsReceipts:
    return await svc.list_receipts(
        _org_id(current_user),
        purchase_order_id=purchase_order_id,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=GoodsReceiptOut, status_code=status.HTTP_201_CREATED)
async def create_goods_receipt(
    data: GoodsReceiptCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: GoodsReceiptService = Depends(_svc),
) -> GoodsReceiptOut:
    try:
        return await svc.create_receipt(
            _org_id(current_user), data, user_id=current_user.user_id
        )
    except PONotFound as exc:
        raise not_found(str(exc))
    except InvalidGRNStatusTransition as exc:
        raise bad_request(str(exc))


@router.get("/{grn_id}", response_model=GoodsReceiptOut)
async def get_goods_receipt(
    grn_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: GoodsReceiptService = Depends(_svc),
) -> GoodsReceiptOut:
    try:
        return await svc.get_receipt(grn_id, _org_id(current_user))
    except GoodsReceiptNotFound as exc:
        raise not_found(str(exc))


@router.post("/{grn_id}/confirm", response_model=GoodsReceiptOut)
async def confirm_goods_receipt(
    grn_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: GoodsReceiptService = Depends(_svc),
) -> GoodsReceiptOut:
    try:
        return await svc.confirm_receipt(
            grn_id, _org_id(current_user), user_id=current_user.user_id
        )
    except (GoodsReceiptNotFound, PONotFound) as exc:
        raise not_found(str(exc))
    except InvalidGRNStatusTransition as exc:
        raise bad_request(str(exc))


@router.post("/{grn_id}/cancel")
async def cancel_goods_receipt(
    grn_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: GoodsReceiptService = Depends(_svc),
) -> dict[str, str]:
    try:
        await svc.cancel_receipt(
            grn_id, _org_id(current_user), user_id=current_user.user_id
        )
        return {"status": "cancelled", "grn_id": str(grn_id)}
    except GoodsReceiptNotFound as exc:
        raise not_found(str(exc))
    except InvalidGRNStatusTransition as exc:
        raise bad_request(str(exc))
