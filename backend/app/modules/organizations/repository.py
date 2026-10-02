"""
app/modules/organizations/repository.py — DB access layer for organizations.

Rules enforced here:
  - Every query on a tenant-scoped table REQUIRES org_id as a non-defaulted arg.
  - companies / organization_members may be read cross-org only by platform_admin
    logic upstream — this layer always scopes by org.
  - No business logic lives here; only DB operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.organizations.schemas import (
    MemberInvite,
    MemberUpdate,
    OrganizationCreate,
    OrganizationUpdate,
)


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── Organization CRUD ──────────────────────────────────────────────────

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self._s.execute(
            select(Organization).where(
                Organization.id == org_id,
                Organization.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_clerk_org_id(self, clerk_org_id: str) -> Organization | None:
        result = await self._s.execute(
            select(Organization).where(
                Organization.clerk_org_id == clerk_org_id,
                Organization.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self._s.execute(
            select(Organization).where(
                Organization.slug == slug,
                Organization.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, payload: OrganizationCreate, *, created_by: str
    ) -> Organization:
        org = Organization(
            clerk_org_id=payload.clerk_org_id,
            name=payload.name,
            slug=payload.slug,
            industry=payload.industry,
            country=payload.country.upper() if payload.country else None,
            created_by=created_by,
            updated_by=created_by,
        )
        self._s.add(org)
        await self._s.flush()  # populate id / server defaults
        return org

    async def update(
        self,
        org: Organization,
        payload: OrganizationUpdate,
        *,
        updated_by: str,
    ) -> Organization:
        if payload.name is not None:
            org.name = payload.name
        if payload.industry is not None:
            org.industry = payload.industry
        if payload.country is not None:
            org.country = payload.country.upper()
        if payload.company_id is not None:
            org.company_id = payload.company_id
        if payload.onboarding_completed is not None:
            if payload.onboarding_completed:
                org.onboarding_completed_at = datetime.now(tz=timezone.utc)
            else:
                org.onboarding_completed_at = None
        if payload.settings is not None:
            # Merge rather than replace so callers can patch individual keys
            existing: dict = dict(org.settings or {})
            existing.update(payload.settings)
            org.settings = existing
        org.updated_by = updated_by
        await self._s.flush()
        return org

    async def mark_onboarding_complete(
        self, org: Organization, *, updated_by: str
    ) -> Organization:
        org.onboarding_completed_at = datetime.now(tz=timezone.utc)
        org.updated_by = updated_by
        await self._s.flush()
        return org

    # ── Members ────────────────────────────────────────────────────────────

    async def get_member(
        self, org_id: uuid.UUID, user_id: str
    ) -> OrganizationMember | None:
        result = await self._s.execute(
            select(OrganizationMember).where(
                OrganizationMember.org_id == org_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self, org_id: uuid.UUID
    ) -> list[OrganizationMember]:
        result = await self._s.execute(
            select(OrganizationMember)
            .where(
                OrganizationMember.org_id == org_id,
                OrganizationMember.deleted_at.is_(None),
            )
            .order_by(OrganizationMember.created_at)
        )
        return list(result.scalars().all())

    async def count_members(self, org_id: uuid.UUID) -> int:
        result = await self._s.execute(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.org_id == org_id,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        return result.scalar_one()

    async def add_member(
        self,
        org_id: uuid.UUID,
        payload: MemberInvite,
        *,
        created_by: str,
    ) -> OrganizationMember:
        member = OrganizationMember(
            org_id=org_id,
            user_id=payload.user_id,
            role=payload.role,
            persona=payload.persona,
            invited_at=datetime.now(tz=timezone.utc),
            created_by=created_by,
            updated_by=created_by,
        )
        self._s.add(member)
        await self._s.flush()
        return member

    async def update_member(
        self,
        member: OrganizationMember,
        payload: MemberUpdate,
        *,
        updated_by: str,
    ) -> OrganizationMember:
        if payload.role is not None:
            member.role = payload.role
        if payload.persona is not None:
            member.persona = payload.persona
        if payload.assigned_categories is not None:
            member.assigned_categories = payload.assigned_categories
        member.updated_by = updated_by
        await self._s.flush()
        return member

    async def remove_member(
        self, member: OrganizationMember, *, updated_by: str
    ) -> None:
        member.deleted_at = datetime.now(tz=timezone.utc)
        member.updated_by = updated_by
        await self._s.flush()

    async def upsert_member_from_webhook(
        self,
        org_id: uuid.UUID,
        user_id: str,
        role: str,
        *,
        actor: str = "system:clerk_webhook",
    ) -> OrganizationMember:
        """
        Create-or-update a member record from a Clerk webhook event.
        Used by the webhook handler; not a user-facing operation.
        """
        existing = await self.get_member(org_id, user_id)
        if existing is not None:
            existing.role = role
            existing.updated_by = actor
            if existing.joined_at is None:
                existing.joined_at = datetime.now(tz=timezone.utc)
            await self._s.flush()
            return existing

        member = OrganizationMember(
            org_id=org_id,
            user_id=user_id,
            role=role,
            joined_at=datetime.now(tz=timezone.utc),
            created_by=actor,
            updated_by=actor,
        )
        self._s.add(member)
        await self._s.flush()
        return member
