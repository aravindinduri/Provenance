"""
/v1/material-requests — Purchase requisition lifecycle

GET    /material-requests              list
POST   /material-requests              create (draft)
GET    /material-requests/{id}         get one
PATCH  /material-requests/{id}         update (draft only)
POST   /material-requests/{id}/submit  submit for approval
POST   /material-requests/{id}/cancel  cancel
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.procurement.schemas import (
    MaterialRequestCreate,
    MaterialRequestOut,
    MaterialRequestUpdate,
    PaginatedMaterialRequests,
)
from app.modules.procurement.service import (
    InvalidStatusTransition,
    MRNotFound,
    ProcurementService,
)

router = APIRouter(prefix="/material-requests", tags=["material-requests"])


def _svc(db: AsyncSession = Depends(get_db)) -> ProcurementService:
    return ProcurementService(db)


def _org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("org_id required")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedMaterialRequests)
async def list_mrs(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProcurementService = Depends(_svc),
) -> PaginatedMaterialRequests:
    return await svc.list_mrs(
        _org_id(current_user), status=status_filter, limit=limit, offset=offset
    )


@router.post("", response_model=MaterialRequestOut, status_code=status.HTTP_201_CREATED)
async def create_mr(
    data: MaterialRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProcurementService = Depends(_svc),
) -> MaterialRequestOut:
    mr = await svc.create_mr(_org_id(current_user), data, user_id=current_user.user_id)
    return MaterialRequestOut.model_validate(mr)


@router.get("/{mr_id}", response_model=MaterialRequestOut)
async def get_mr(
    mr_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProcurementService = Depends(_svc),
) -> MaterialRequestOut:
    try:
        mr = await svc.get_mr(mr_id, _org_id(current_user))
    except MRNotFound:
        raise not_found("Material request not found")
    return MaterialRequestOut.model_validate(mr)


@router.patch("/{mr_id}", response_model=MaterialRequestOut)
async def update_mr(
    mr_id: uuid.UUID,
    data: MaterialRequestUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProcurementService = Depends(_svc),
) -> MaterialRequestOut:
    try:
        mr = await svc.update_mr(mr_id, _org_id(current_user), data, user_id=current_user.user_id)
    except MRNotFound:
        raise not_found("Material request not found")
    except InvalidStatusTransition as exc:
        raise bad_request(str(exc))
    return MaterialRequestOut.model_validate(mr)


@router.post("/{mr_id}/submit", response_model=MaterialRequestOut)
async def submit_mr(
    mr_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProcurementService = Depends(_svc),
) -> MaterialRequestOut:
    try:
        mr = await svc.submit_mr(mr_id, _org_id(current_user), user_id=current_user.user_id)
    except MRNotFound:
        raise not_found("Material request not found")
    except InvalidStatusTransition as exc:
        raise bad_request(str(exc))
    return MaterialRequestOut.model_validate(mr)


@router.post("/{mr_id}/cancel", response_model=MaterialRequestOut)
async def cancel_mr(
    mr_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ProcurementService = Depends(_svc),
) -> MaterialRequestOut:
    try:
        mr = await svc.cancel_mr(mr_id, _org_id(current_user), user_id=current_user.user_id)
    except MRNotFound:
        raise not_found("Material request not found")
    except InvalidStatusTransition as exc:
        raise bad_request(str(exc))
    return MaterialRequestOut.model_validate(mr)
