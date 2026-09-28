"""
GET /v1/auth/me — returns the current authenticated user plus their org context.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import MeOut, OrganizationOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=MeOut,
    summary="Current authenticated user + org context",
)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    """
    Returns the resolved CurrentUser and their organization record.

    This is the canonical first call a frontend makes after sign-in to
    discover the user's org UUID, role, and persona.
    """
    org_out = None
    if current_user.org_id:
        repo = OrganizationRepository(db)
        org = await repo.get_by_id(uuid.UUID(current_user.org_id))
        if org is not None:
            org_out = OrganizationOut.model_validate(org)

    return MeOut(
        user_id=current_user.user_id,
        email=current_user.email,
        org_id=current_user.org_id,
        clerk_org_id=current_user.clerk_org_id,
        role=current_user.role,
        persona=current_user.persona,
        assigned_categories=current_user.assigned_categories,
        organization=org_out,
    )
