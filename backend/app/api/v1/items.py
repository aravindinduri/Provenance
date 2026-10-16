"""
/v1/items — Material master / item catalog

GET    /items              list (paginated, filterable)
POST   /items              create
GET    /items/{id}         get one
PATCH  /items/{id}         update
DELETE /items/{id}         soft-delete
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.items.schemas import ItemCreate, ItemOut, ItemUpdate, PaginatedItems
from app.modules.items.service import DuplicateItemCode, ItemNotFound, ItemService

router = APIRouter(prefix="/items", tags=["items"])


def _svc(db: AsyncSession = Depends(get_db)) -> ItemService:
    return ItemService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedItems)
async def list_items(
    q: str | None = Query(None, description="Search by name or item_code"),
    category: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(_svc),
) -> PaginatedItems:
    org_id = _org_id(current_user)
    return await svc.list_items(org_id, q=q, category=category, is_active=is_active, limit=limit, offset=offset)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(_svc),
) -> ItemOut:
    org_id = _org_id(current_user)
    try:
        item = await svc.create_item(org_id, data, created_by=current_user.user_id)
    except DuplicateItemCode as exc:
        raise bad_request(str(exc))
    return ItemOut.model_validate(item)


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(
    item_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(_svc),
) -> ItemOut:
    org_id = _org_id(current_user)
    try:
        item = await svc.get_item(item_id, org_id)
    except ItemNotFound:
        raise not_found("Item not found")
    return ItemOut.model_validate(item)


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: uuid.UUID,
    data: ItemUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(_svc),
) -> ItemOut:
    org_id = _org_id(current_user)
    try:
        item = await svc.update_item(item_id, org_id, data, updated_by=current_user.user_id)
    except ItemNotFound:
        raise not_found("Item not found")
    return ItemOut.model_validate(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_item(
    item_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ItemService = Depends(_svc),
) -> Response:
    org_id = _org_id(current_user)
    try:
        await svc.delete_item(item_id, org_id)
    except ItemNotFound:
        raise not_found("Item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
