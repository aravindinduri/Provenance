"""
/v1/graph — Supply chain topology graph visualization and path finding.

Per arch §8, §13, and Phase 7:
  GET /graph        — node/edge payload, capped, recursive CTE traversal with cycle guard
  GET /graph/paths  — explain connection / trace exposure path from source to target
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import bad_request
from app.db.session import get_db
from app.modules.graph.schemas import GraphData, GraphPathsResponse
from app.modules.graph.service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


def _service(db: AsyncSession) -> GraphService:
    return GraphService(db)


def _get_org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("Tenant org_id is required for graph operations")
    return uuid.UUID(current_user.org_id)


@router.get(
    "",
    response_model=GraphData,
    summary="Get supply chain topology graph for visualization",
    description="Traverses the tenant's supply network using recursive CTE with cycle guard, depth cap (1-5), and node cap.",
)
async def get_graph(
    request: Request,
    root: uuid.UUID | None = Query(None, description="Optional root company ID to center traversal around"),
    depth: int = Query(3, ge=1, le=5, description="Traversal depth cap (1-5, default 3)"),
    types: str | None = Query(None, description="Comma-separated relationship types (e.g. supplies_to,sub_supplies_to,owned_by,located_in)"),
    limit: int = Query(300, ge=1, le=5000, description="Node/edge payload cap (default 300, max 5000)"),
    current_user: CurrentUser = Depends(require_permission("graph:read")),
    db: AsyncSession = Depends(get_db),
) -> GraphData:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    parsed_types = [t.strip() for t in types.split(",") if t.strip()] if types else None

    svc = _service(db)
    return await svc.get_graph(
        org_id=org_id,
        root=root,
        depth=depth,
        types=parsed_types,
        limit=limit,
    )


@router.get(
    "/paths",
    response_model=GraphPathsResponse,
    summary="Find and explain exposure paths between entities",
    description="Traces multi-tier directed paths from an upstream company to the tenant organization or downstream target.",
)
async def get_graph_paths(
    request: Request,
    from_id: uuid.UUID = Query(..., alias="from", description="Source company ID"),
    to_id: uuid.UUID | None = Query(None, alias="to", description="Target company or org ID (defaults to org)"),
    max_depth: int = Query(5, ge=1, le=5, description="Maximum traversal depth (1-5, default 5)"),
    current_user: CurrentUser = Depends(require_permission("graph:read")),
    db: AsyncSession = Depends(get_db),
) -> GraphPathsResponse:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    return await svc.get_paths(
        org_id=org_id,
        from_id=from_id,
        to_id=to_id,
        max_depth=max_depth,
    )
