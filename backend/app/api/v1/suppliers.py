"""
/v1/suppliers — Direct supplier management for the tenant.

Endpoints:
  GET    /suppliers             — list tenant's suppliers (cursor-paginated)
  POST   /suppliers             — add a supplier to tenant
  GET    /suppliers/{id}        — get supplier details
  PATCH  /suppliers/{id}        — update supplier attributes
  DELETE /suppliers/{id}        — soft-delete supplier
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import bad_request, not_found
from app.core.pagination import PaginationMeta
from app.db.session import get_db
from app.modules.companies.service import CompanyNotFound
from app.modules.graph.schemas import (
    PaginatedSuppliers,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)
from app.modules.graph.service import GraphService, SupplierNotFound

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _service(db: AsyncSession) -> GraphService:
    return GraphService(db)


def _get_org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("Tenant org_id is required for supplier operations")
    return uuid.UUID(current_user.org_id)


@router.get(
    "",
    response_model=PaginatedSuppliers,
    summary="List organization suppliers",
)
async def list_suppliers(
    request: Request,
    category: str | None = Query(None, description="Filter by category"),
    criticality: int | None = Query(None, ge=1, le=5, description="Filter by criticality (1-5)"),
    tier: int | None = Query(None, ge=1, le=10, description="Filter by tier"),
    active_only: bool = Query(True, description="Only return active suppliers"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSuppliers:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    items, next_cursor, has_more = await svc.list_suppliers(
        org_id=org_id,
        category=category,
        criticality=criticality,
        tier=tier,
        active_only=active_only,
        cursor=cursor,
        limit=limit,
    )

    return PaginatedSuppliers(
        data=items,
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )


@router.post(
    "",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a supplier to the organization",
)
async def create_supplier(
    request: Request,
    payload: SupplierCreate,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> SupplierOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        supplier = await svc.create_supplier(org_id, payload)
        await db.commit()
        return supplier
    except CompanyNotFound as exc:
        return not_found(request, detail=str(exc))  # type: ignore[return-value]


@router.get(
    "/{supplier_id}",
    response_model=SupplierOut,
    summary="Get supplier details",
)
async def get_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> SupplierOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        return await svc.get_supplier(supplier_id, org_id)
    except SupplierNotFound:
        return not_found(request, detail=f"Supplier {supplier_id} not found")  # type: ignore[return-value]


@router.patch(
    "/{supplier_id}",
    response_model=SupplierOut,
    summary="Update supplier attributes",
)
async def update_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> SupplierOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        supplier = await svc.update_supplier(supplier_id, org_id, payload)
        await db.commit()
        return supplier
    except SupplierNotFound:
        return not_found(request, detail=f"Supplier {supplier_id} not found")  # type: ignore[return-value]


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Soft-delete supplier",
)
async def delete_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        await svc.delete_supplier(supplier_id, org_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except SupplierNotFound:
        return not_found(request, detail=f"Supplier {supplier_id} not found")  # type: ignore[return-value]
