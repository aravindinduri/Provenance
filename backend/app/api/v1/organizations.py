"""
/v1/organizations — organization CRUD and member management.

Endpoints:
  GET  /organizations/{id}           — fetch org (member or platform_admin)
  PATCH /organizations/{id}          — update org settings (org_admin)
  GET  /organizations/{id}/members   — list members
  POST /organizations/{id}/members   — invite a member (org_admin)
  PATCH /organizations/{id}/members/{user_id} — update role/persona (org_admin)
  DELETE /organizations/{id}/members/{user_id} — remove member (org_admin)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import AuthorizationError, CurrentUser
from app.core.deps import get_current_user, require_permission
from app.core.errors import (
    conflict,
    forbidden,
    not_found,
)
from app.db.session import get_db
from app.modules.organizations.schemas import (
    MemberInvite,
    MemberOut,
    MemberUpdate,
    OrganizationOut,
    OrganizationUpdate,
    PaginatedMembers,
)
from app.modules.organizations.service import (
    MemberAlreadyExists,
    MemberNotFound,
    OrganizationNotFound,
    OrganizationService,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _service(db: AsyncSession) -> OrganizationService:
    return OrganizationService(db)


# ── Organization endpoints ────────────────────────────────────────────────────

@router.get(
    "/{org_id}",
    response_model=OrganizationOut,
    summary="Get organization",
)
async def get_organization(
    request: Request,
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationOut:
    svc = _service(db)
    try:
        org = await svc.get_org_for_user(org_id, current_user)
    except OrganizationNotFound:
        return not_found(request, detail=f"Organization {org_id} not found")  # type: ignore[return-value]
    except AuthorizationError as exc:
        return forbidden(request, detail=exc.detail)  # type: ignore[return-value]
    return OrganizationOut.model_validate(org)


@router.patch(
    "/{org_id}",
    response_model=OrganizationOut,
    summary="Update organization settings",
)
async def update_organization(
    request: Request,
    org_id: uuid.UUID,
    payload: OrganizationUpdate,
    current_user: CurrentUser = Depends(require_permission("org:write")),
    db: AsyncSession = Depends(get_db),
) -> OrganizationOut:
    svc = _service(db)
    try:
        org = await svc.update_org(org_id, payload, current_user=current_user)
    except OrganizationNotFound:
        return not_found(request, detail=f"Organization {org_id} not found")  # type: ignore[return-value]
    except AuthorizationError as exc:
        return forbidden(request, detail=exc.detail)  # type: ignore[return-value]
    await db.commit()
    return OrganizationOut.model_validate(org)


# ── Member endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/{org_id}/members",
    response_model=PaginatedMembers,
    summary="List organization members",
)
async def list_members(
    request: Request,
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("members:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedMembers:
    svc = _service(db)
    try:
        members = await svc.list_members(org_id, current_user)
    except OrganizationNotFound:
        return not_found(request, detail=f"Organization {org_id} not found")  # type: ignore[return-value]
    except AuthorizationError as exc:
        return forbidden(request, detail=exc.detail)  # type: ignore[return-value]
    return PaginatedMembers(
        data=[MemberOut.model_validate(m) for m in members],
        total=len(members),
    )


@router.post(
    "/{org_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a member",
)
async def invite_member(
    request: Request,
    org_id: uuid.UUID,
    payload: MemberInvite,
    current_user: CurrentUser = Depends(require_permission("members:write")),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    svc = _service(db)
    try:
        member = await svc.invite_member(org_id, payload, current_user=current_user)
    except OrganizationNotFound:
        return not_found(request, detail=f"Organization {org_id} not found")  # type: ignore[return-value]
    except AuthorizationError as exc:
        return forbidden(request, detail=exc.detail)  # type: ignore[return-value]
    except MemberAlreadyExists as exc:
        return conflict(request, detail=str(exc))  # type: ignore[return-value]
    await db.commit()
    return MemberOut.model_validate(member)


@router.patch(
    "/{org_id}/members/{user_id}",
    response_model=MemberOut,
    summary="Update a member's role or persona",
)
async def update_member(
    request: Request,
    org_id: uuid.UUID,
    user_id: str,
    payload: MemberUpdate,
    current_user: CurrentUser = Depends(require_permission("members:write")),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    svc = _service(db)
    try:
        member = await svc.update_member(
            org_id, user_id, payload, current_user=current_user
        )
    except OrganizationNotFound:
        return not_found(request, detail=f"Organization {org_id} not found")  # type: ignore[return-value]
    except MemberNotFound:
        return not_found(request, detail=f"Member {user_id} not found")  # type: ignore[return-value]
    except AuthorizationError as exc:
        return forbidden(request, detail=exc.detail)  # type: ignore[return-value]
    await db.commit()
    return MemberOut.model_validate(member)


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove a member from the organization",
)
async def remove_member(
    request: Request,
    org_id: uuid.UUID,
    user_id: str,
    current_user: CurrentUser = Depends(require_permission("members:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    svc = _service(db)
    try:
        await svc.remove_member(org_id, user_id, current_user=current_user)
    except OrganizationNotFound:
        return not_found(request, detail=f"Organization {org_id} not found")  # type: ignore[return-value]
    except MemberNotFound:
        return not_found(request, detail=f"Member {user_id} not found")  # type: ignore[return-value]
    except AuthorizationError as exc:
        return forbidden(request, detail=exc.detail)  # type: ignore[return-value]
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
