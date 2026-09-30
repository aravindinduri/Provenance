"""
/v1/companies — Canonical company search and profile.

Endpoints:
  GET /companies/search?q=&country=&cursor=&limit= — search canonical registry
  GET /companies/{id}                             — enriched profile + identifiers + locations
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import not_found
from app.core.pagination import PaginationMeta
from app.db.session import get_db
from app.modules.companies.schemas import (
    CompanyDetailOut,
    CompanySummaryOut,
    PaginatedCompanies,
)
from app.modules.companies.service import CompanyNotFound, CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


def _service(db: AsyncSession) -> CompanyService:
    return CompanyService(db)


@router.get(
    "/search",
    response_model=PaginatedCompanies,
    summary="Search canonical companies",
)
async def search_companies(
    request: Request,
    q: str | None = Query(None, description="Search term for company legal name"),
    country: str | None = Query(
        None, min_length=2, max_length=2, description="2-letter ISO country code"
    ),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCompanies:
    svc = _service(db)
    items, next_cursor, has_more = await svc.search_companies(
        q=q,
        country=country,
        cursor=cursor,
        limit=limit,
    )

    return PaginatedCompanies(
        data=[CompanySummaryOut.model_validate(c) for c in items],
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )


@router.get(
    "/{company_id}",
    response_model=CompanyDetailOut,
    summary="Get enriched company profile",
)
async def get_company(
    request: Request,
    company_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> CompanyDetailOut:
    svc = _service(db)
    try:
        return await svc.get_company_detail(company_id)
    except CompanyNotFound:
        return not_found(request, detail=f"Company {company_id} not found")  # type: ignore[return-value]
