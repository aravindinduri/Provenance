"""
app/modules/organizations/service.py — business logic for organizations.

Sits between the API layer (routers) and the DB layer (repository).
Raises domain exceptions that the router converts to HTTP responses.
"""

from __future__ import annotations

import re
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import AuthorizationError, CurrentUser
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import (
    MemberInvite,
    MemberUpdate,
    OrganizationCreate,
    OrganizationUpdate,
)

logger = structlog.get_logger(__name__)


class OrganizationNotFound(Exception):
    pass


class MemberNotFound(Exception):
    pass


class MemberAlreadyExists(Exception):
    pass


class SlugConflict(Exception):
    pass


def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100]


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = OrganizationRepository(session)
        self._session = session

    # ── Organization ───────────────────────────────────────────────────────

    async def get_org(self, org_id: uuid.UUID) -> Organization:
        org = await self._repo.get_by_id(org_id)
        if org is None:
            raise OrganizationNotFound(f"Organization {org_id} not found")
        return org

    async def get_org_for_user(
        self, org_id: uuid.UUID, current_user: CurrentUser
    ) -> Organization:
        """
        Retrieve an org, enforcing that the caller belongs to it
        (unless they are a platform_admin).
        """
        org = await self.get_org(org_id)
        if not current_user.is_platform_admin:
            if current_user.org_id != str(org_id):
                raise AuthorizationError(
                    "You do not have access to this organization."
                )
        return org

    async def update_org(
        self,
        org_id: uuid.UUID,
        payload: OrganizationUpdate,
        *,
        current_user: CurrentUser,
    ) -> Organization:
        org = await self.get_org_for_user(org_id, current_user)
        if payload.company_id is not None:
            from app.modules.companies.repository import CompanyRepository
            from app.modules.companies.service import CompanyNotFound

            comp_repo = CompanyRepository(self._session)
            comp = await comp_repo.get_by_id(payload.company_id)
            if comp is None:
                raise CompanyNotFound(payload.company_id)
        return await self._repo.update(org, payload, updated_by=current_user.user_id)

    async def create_from_webhook(
        self, payload: OrganizationCreate, *, actor: str = "system:clerk_webhook"
    ) -> Organization:
        """
        Create a new organization triggered by a Clerk webhook.
        Generates a unique slug if there is a conflict.
        """
        base_slug = _slugify(payload.slug or payload.name)
        slug = base_slug
        attempt = 0
        while await self._repo.get_by_slug(slug) is not None:
            attempt += 1
            slug = f"{base_slug}-{attempt}"
            if attempt > 10:
                # Extremely unlikely; use UUID suffix as fallback
                slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"
                break

        final_payload = OrganizationCreate(
            clerk_org_id=payload.clerk_org_id,
            name=payload.name,
            slug=slug,
            industry=payload.industry,
            country=payload.country,
        )
        return await self._repo.create(final_payload, created_by=actor)

    # ── Members ────────────────────────────────────────────────────────────

    async def list_members(
        self, org_id: uuid.UUID, current_user: CurrentUser
    ) -> list[OrganizationMember]:
        await self.get_org_for_user(org_id, current_user)
        return await self._repo.list_members(org_id)

    async def invite_member(
        self,
        org_id: uuid.UUID,
        payload: MemberInvite,
        *,
        current_user: CurrentUser,
    ) -> OrganizationMember:
        await self.get_org_for_user(org_id, current_user)

        existing = await self._repo.get_member(org_id, payload.user_id)
        if existing is not None:
            raise MemberAlreadyExists(
                f"User {payload.user_id} is already a member of this organization."
            )

        logger.info(
            "org_member_invited",
            org_id=str(org_id),
            invitee=payload.user_id,
            role=payload.role,
            inviter=current_user.user_id,
        )
        return await self._repo.add_member(
            org_id, payload, created_by=current_user.user_id
        )

    async def update_member(
        self,
        org_id: uuid.UUID,
        user_id: str,
        payload: MemberUpdate,
        *,
        current_user: CurrentUser,
    ) -> OrganizationMember:
        await self.get_org_for_user(org_id, current_user)

        member = await self._repo.get_member(org_id, user_id)
        if member is None:
            raise MemberNotFound(f"User {user_id} is not a member of this org.")

        return await self._repo.update_member(
            member, payload, updated_by=current_user.user_id
        )

    async def remove_member(
        self,
        org_id: uuid.UUID,
        user_id: str,
        *,
        current_user: CurrentUser,
    ) -> None:
        await self.get_org_for_user(org_id, current_user)

        member = await self._repo.get_member(org_id, user_id)
        if member is None:
            raise MemberNotFound(f"User {user_id} is not a member of this org.")

        # Prevent removing the last org_admin
        if member.role == "org_admin":
            members = await self._repo.list_members(org_id)
            admin_count = sum(1 for m in members if m.role == "org_admin")
            if admin_count <= 1:
                raise AuthorizationError(
                    "Cannot remove the last org_admin. "
                    "Promote another member first."
                )

        await self._repo.remove_member(member, updated_by=current_user.user_id)

    async def upsert_member_from_webhook(
        self,
        clerk_org_id: str,
        user_id: str,
        clerk_role: str,
    ) -> OrganizationMember | None:
        """
        Sync a member change from a Clerk webhook.
        Returns None if the org doesn't exist yet (will sync on next request).
        """
        from app.auth.providers.clerk import _map_clerk_role

        org = await self._repo.get_by_clerk_org_id(clerk_org_id)
        if org is None:
            logger.warning(
                "clerk_webhook_org_not_found",
                clerk_org_id=clerk_org_id,
                user_id=user_id,
            )
            return None

        role = _map_clerk_role(clerk_role)
        return await self._repo.upsert_member_from_webhook(
            org.id, user_id, role
        )
