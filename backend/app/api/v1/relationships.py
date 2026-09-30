"""
/v1/relationships — Graph relationship management for the tenant.

Endpoints:
  GET    /relationships             — list graph edges (cursor-paginated)
  POST   /relationships             — create relationship edge
  GET    /relationships/{id}        — get relationship details
  PATCH  /relationships/{id}        — update relationship attributes
  DELETE /relationships/{id}        — soft-delete relationship
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
    PaginatedRelationships,
    RelationshipCreate,
    RelationshipOut,
    RelationshipUpdate,
)
from app.modules.graph.service import GraphService, RelationshipNotFound

router = APIRouter(prefix="/relationships", tags=["relationships"])


def _service(db: AsyncSession) -> GraphService:
    return GraphService(db)


def _get_org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("Tenant org_id is required for relationship operations")
    return uuid.UUID(current_user.org_id)


@router.get(
    "",
    response_model=PaginatedRelationships,
    summary="List organization graph relationships",
)
async def list_relationships(
    request: Request,
    relationship_type: str | None = Query(None, description="Filter by relationship type"),
    from_company_id: uuid.UUID | None = Query(None, description="Filter by source company"),
    to_company_id: uuid.UUID | None = Query(None, description="Filter by target company"),
    tier: int | None = Query(None, ge=1, le=10, description="Filter by tier"),
    active_only: bool = Query(True, description="Only return active relationships"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    current_user: CurrentUser = Depends(require_permission("graph:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRelationships:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    items, next_cursor, has_more = await svc.list_relationships(
        org_id=org_id,
        relationship_type=relationship_type,
        from_company_id=from_company_id,
        to_company_id=to_company_id,
        tier=tier,
        active_only=active_only,
        cursor=cursor,
        limit=limit,
    )

    return PaginatedRelationships(
        data=items,
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )


@router.post(
    "",
    response_model=RelationshipOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a graph relationship edge",
)
async def create_relationship(
    request: Request,
    payload: RelationshipCreate,
    current_user: CurrentUser = Depends(require_permission("graph:write")),
    db: AsyncSession = Depends(get_db),
) -> RelationshipOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        rel = await svc.create_relationship(org_id, payload)
        await db.commit()
        return rel
    except CompanyNotFound as exc:
        return not_found(request, detail=str(exc))  # type: ignore[return-value]


@router.get(
    "/{relationship_id}",
    response_model=RelationshipOut,
    summary="Get relationship details",
)
async def get_relationship(
    request: Request,
    relationship_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("graph:read")),
    db: AsyncSession = Depends(get_db),
) -> RelationshipOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        return await svc.get_relationship(relationship_id, org_id)
    except RelationshipNotFound:
        return not_found(request, detail=f"Relationship {relationship_id} not found")  # type: ignore[return-value]


@router.patch(
    "/{relationship_id}",
    response_model=RelationshipOut,
    summary="Update relationship attributes",
)
async def update_relationship(
    request: Request,
    relationship_id: uuid.UUID,
    payload: RelationshipUpdate,
    current_user: CurrentUser = Depends(require_permission("graph:write")),
    db: AsyncSession = Depends(get_db),
) -> RelationshipOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        rel = await svc.update_relationship(relationship_id, org_id, payload)
        await db.commit()
        return rel
    except RelationshipNotFound:
        return not_found(request, detail=f"Relationship {relationship_id} not found")  # type: ignore[return-value]


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Soft-delete relationship",
)
async def delete_relationship(
    request: Request,
    relationship_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("graph:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        await svc.delete_relationship(relationship_id, org_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except RelationshipNotFound:
        return not_found(request, detail=f"Relationship {relationship_id} not found")  # type: ignore[return-value]
