"""
/v1/entity-reviews — Human review queue for ambiguous entity resolutions (Stage 7).

Architecture reference: §G.1 Stage 7, §10 (Agent 2), §N.2.
Endpoints:
  GET  /entity-reviews             — list pending/resolved entity reviews
  POST /entity-reviews/{id}/resolve — resolve review by matching, creating new, or rejecting
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import bad_request, not_found
from app.core.pagination import PaginationMeta
from app.db.session import get_db
from app.modules.companies.models import Company, EntityResolutionReview
from app.modules.companies.schemas import (
    CompanySummaryOut,
    EntityResolutionReviewOut,
    EntityReviewResolveRequest,
    PaginatedEntityReviews,
)
from app.modules.companies.service import CompanyService

router = APIRouter(prefix="/entity-reviews", tags=["entity-reviews"])


@router.get(
    "",
    response_model=PaginatedEntityReviews,
    summary="List entity resolution reviews",
)
async def list_entity_reviews(
    request: Request,
    review_status: str | None = Query("pending", alias="status", description="Review status filter"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedEntityReviews:
    stmt = select(EntityResolutionReview)
    if review_status:
        stmt = stmt.where(EntityResolutionReview.status == review_status)

    if current_user.org_id:
        # Show tenant-scoped reviews and global reviews
        user_org_uuid = uuid.UUID(current_user.org_id)
        stmt = stmt.where(
            (EntityResolutionReview.org_id == user_org_uuid) | (EntityResolutionReview.org_id.is_(None))
        )

    stmt = stmt.order_by(EntityResolutionReview.created_at.desc()).limit(limit + 1)
    res = await db.execute(stmt)
    rows = list(res.scalars().all())

    has_more = len(rows) > limit
    items = rows[:limit]

    # Pre-fetch suggested companies for display
    suggested_ids = [r.suggested_company_id for r in items if r.suggested_company_id]
    comp_map: dict[uuid.UUID, Company] = {}
    if suggested_ids:
        c_stmt = select(Company).where(Company.id.in_(suggested_ids))
        c_res = await db.execute(c_stmt)
        comp_map = {c.id: c for c in c_res.scalars().all()}

    out_items: list[EntityResolutionReviewOut] = []
    for r in items:
        suggested_comp = comp_map.get(r.suggested_company_id) if r.suggested_company_id else None
        item_out = EntityResolutionReviewOut(
            id=r.id,
            org_id=r.org_id,
            raw_name=r.raw_name,
            context=r.context or {},
            candidates=r.candidates or [],
            suggested_company_id=r.suggested_company_id,
            suggested_company=CompanySummaryOut.model_validate(suggested_comp) if suggested_comp else None,
            ai_confidence=float(r.ai_confidence) if r.ai_confidence is not None else None,
            ai_reasoning=r.ai_reasoning,
            status=r.status,
            resolved_company_id=r.resolved_company_id,
            resolved_by=r.resolved_by,
            resolved_at=r.resolved_at,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        out_items.append(item_out)

    return PaginatedEntityReviews(
        data=out_items,
        pagination=PaginationMeta(next_cursor=None, has_more=has_more),
    )


@router.post(
    "/{review_id}/resolve",
    response_model=EntityResolutionReviewOut,
    summary="Resolve an entity review item",
)
async def resolve_entity_review(
    request: Request,
    review_id: uuid.UUID,
    payload: EntityReviewResolveRequest,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> EntityResolutionReviewOut:
    stmt = select(EntityResolutionReview).where(EntityResolutionReview.id == review_id)
    res = await db.execute(stmt)
    review = res.scalar_one_or_none()
    if not review:
        return not_found(request, detail=f"Entity review {review_id} not found")  # type: ignore[return-value]

    action = payload.action.lower()
    now = datetime.now(timezone.utc)
    user_identifier = current_user.user_id or "system_user"

    if action == "match":
        if not payload.company_id:
            return bad_request(request, detail="company_id is required when action is 'match'")  # type: ignore[return-value]

        c_stmt = select(Company).where(Company.id == payload.company_id, Company.deleted_at.is_(None))
        c_res = await db.execute(c_stmt)
        target_comp = c_res.scalar_one_or_none()
        if not target_comp:
            return not_found(request, detail=f"Company {payload.company_id} not found")  # type: ignore[return-value]

        review.status = "resolved"
        review.resolved_company_id = target_comp.id
        review.resolved_by = user_identifier
        review.resolved_at = now

    elif action == "reject":
        review.status = "rejected"
        review.resolved_by = user_identifier
        review.resolved_at = now

    elif action == "create_new":
        company_svc = CompanyService(db)
        legal_name = payload.legal_name or review.raw_name
        country = payload.country or review.context.get("country")

        new_company = await company_svc.get_or_create_by_name(
            legal_name=legal_name,
            country=country,
            primary_domain=review.context.get("domain"),
        )
        review.status = "new_entity"
        review.resolved_company_id = new_company.id
        review.resolved_by = user_identifier
        review.resolved_at = now

    else:
        return bad_request(request, detail=f"Unsupported action '{payload.action}'. Use 'match', 'reject', or 'create_new'.")  # type: ignore[return-value]

    await db.flush()

    return EntityResolutionReviewOut.model_validate(review)
