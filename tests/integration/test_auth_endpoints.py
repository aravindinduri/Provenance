"""
tests/integration/test_auth_endpoints.py

HTTP-level integration tests for the Phase 3 auth layer.

Strategy: we patch ClerkVerifier.verify() so no real Clerk JWKS is needed,
then drive actual HTTP requests through the FastAPI app using httpx's
ASGITransport. The DB is the test database from conftest.py (same pattern as
the existing Phase 2 security tests).

Coverage:
  A. Token rejection — missing / malformed / expired tokens → 401
  B. Permission guard — correct role passes, wrong role → 403
  C. GET /v1/auth/me — returns correct MeOut shape
  D. GET /v1/organizations/{id} — own org readable, foreign org → 403
  E. PATCH /v1/organizations/{id} — org_admin can update, org_user cannot
  F. GET /v1/organizations/{id}/members — members:read required
  G. POST /v1/organizations/{id}/members — members:write required
  H. RFC 9457 error shape — all error responses have type/title/status/detail
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.base import (
    AuthenticationError,
    CurrentUser,
    ROLE_ANALYST,
    ROLE_ORG_ADMIN,
    ROLE_ORG_USER,
    ROLE_READ_ONLY,
)
from app.main import app

# ---------------------------------------------------------------------------
# Async DB fixtures (mirrors Phase 2 conftest but async)
# ---------------------------------------------------------------------------

import os, re

def _async_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://provenance:provenance@localhost:5432/provenance_test",
    )
    # ensure asyncpg driver
    return re.sub(r"^postgresql(\+psycopg2)?", "postgresql+asyncpg", url)


@pytest.fixture(scope="module")
async def async_engine():
    engine = create_async_engine(_async_url(), echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_db(async_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text("SET LOCAL row_security = off;"))
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Helper: pre-insert an org + member using raw SQL (same as conftest factories)
# ---------------------------------------------------------------------------

async def _create_org_and_member(
    session: AsyncSession,
    *,
    user_id: str,
    role: str,
    slug_suffix: str = "",
) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (org_id, company_id) after inserting org + member into the test DB."""
    company_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO companies (id, legal_name, name_norm, created_at, updated_at) "
            "VALUES (:id, :ln, :nn, NOW(), NOW())"
        ),
        {"id": company_id, "ln": f"Test Corp {slug_suffix}", "nn": f"test corp {slug_suffix}"},
    )

    org_id = uuid.uuid4()
    clerk_org_id = f"clerk_org_{slug_suffix}_{uuid.uuid4().hex[:6]}"
    await session.execute(
        text(
            "INSERT INTO organizations "
            "(id, clerk_org_id, name, slug, company_id, created_at, updated_at) "
            "VALUES (:id, :cok, :name, :slug, :cid, NOW(), NOW())"
        ),
        {
            "id": org_id,
            "cok": clerk_org_id,
            "name": f"Test Org {slug_suffix}",
            "slug": f"test-org-{slug_suffix}-{uuid.uuid4().hex[:6]}",
            "cid": company_id,
        },
    )

    await session.execute(
        text(
            "INSERT INTO organization_members "
            "(id, org_id, user_id, role, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :oid, :uid, :role, NOW(), NOW())"
        ),
        {"oid": org_id, "uid": user_id, "role": role},
    )
    await session.flush()
    return org_id, company_id


# ---------------------------------------------------------------------------
# Helper: build a CurrentUser and patch the verifier
# ---------------------------------------------------------------------------

def _make_user(
    *,
    user_id: str = "user_test",
    org_id: str | None = None,
    clerk_org_id: str | None = "clerk_org_test",
    role: str = ROLE_ORG_USER,
) -> CurrentUser:
    return CurrentUser(
        user_id=user_id,
        org_id=org_id,
        clerk_org_id=clerk_org_id,
        role=role,
        email=f"{user_id}@test.com",
    )


def _patch_verifier(user: CurrentUser):
    """Context manager that makes ClerkVerifier.verify() return *user*."""
    return patch(
        "app.auth.providers.clerk.ClerkVerifier.verify",
        new=AsyncMock(return_value=user),
    )


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# A. Token rejection
# ---------------------------------------------------------------------------

class TestTokenRejection:
    async def test_missing_authorization_header_returns_401(
        self, client: AsyncClient
    ) -> None:
        r = await client.get("/v1/auth/me")
        assert r.status_code == 401

    async def test_non_bearer_scheme_returns_401(
        self, client: AsyncClient
    ) -> None:
        r = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert r.status_code == 401

    async def test_expired_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.auth.providers.clerk.ClerkVerifier.verify",
            new=AsyncMock(side_effect=AuthenticationError("Token has expired")),
        ):
            r = await client.get(
                "/v1/auth/me",
                headers={"Authorization": "Bearer expired.token.here"},
            )
        assert r.status_code == 401

    async def test_401_body_is_rfc9457(self, client: AsyncClient) -> None:
        r = await client.get("/v1/auth/me")
        body = r.json()
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert body["status"] == 401
        assert "detail" in body

    async def test_403_body_is_rfc9457(self, client: AsyncClient) -> None:
        read_only_user = _make_user(role=ROLE_READ_ONLY, org_id=str(uuid.uuid4()))
        with _patch_verifier(read_only_user):
            r = await client.patch(
                f"/v1/organizations/{uuid.uuid4()}",
                json={"name": "New Name"},
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 403
        body = r.json()
        assert body["status"] == 403
        assert "type" in body


# ---------------------------------------------------------------------------
# B. Permission guard
# ---------------------------------------------------------------------------

class TestPermissionGuard:
    async def test_read_only_cannot_patch_org(
        self, client: AsyncClient
    ) -> None:
        user = _make_user(role=ROLE_READ_ONLY, org_id=str(uuid.uuid4()))
        with _patch_verifier(user):
            r = await client.patch(
                f"/v1/organizations/{uuid.uuid4()}",
                json={"name": "x"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 403

    async def test_org_user_cannot_patch_org(
        self, client: AsyncClient
    ) -> None:
        user = _make_user(role=ROLE_ORG_USER, org_id=str(uuid.uuid4()))
        with _patch_verifier(user):
            r = await client.patch(
                f"/v1/organizations/{uuid.uuid4()}",
                json={"name": "x"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 403

    async def test_analyst_cannot_invite_members(
        self, client: AsyncClient
    ) -> None:
        user = _make_user(role=ROLE_ANALYST, org_id=str(uuid.uuid4()))
        with _patch_verifier(user):
            r = await client.post(
                f"/v1/organizations/{uuid.uuid4()}/members",
                json={"user_id": "new_user", "role": "org_user"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 403

    async def test_org_admin_can_reach_members_endpoint(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="admin_user", role=ROLE_ORG_ADMIN, slug_suffix="perm-a"
        )
        user = _make_user(
            user_id="admin_user", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.get(
                f"/v1/organizations/{org_id}/members",
                headers={"Authorization": "Bearer t"},
            )
        # 200 means the permission guard passed (may be 404 for unknown org — both are fine)
        assert r.status_code in {200, 404}
        assert r.status_code != 403


# ---------------------------------------------------------------------------
# C. GET /v1/auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    async def test_returns_200_with_user_shape(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="me_user", role=ROLE_ANALYST, slug_suffix="me-a"
        )
        user = _make_user(
            user_id="me_user", role=ROLE_ANALYST, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.get(
                "/v1/auth/me", headers={"Authorization": "Bearer t"}
            )
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == "me_user"
        assert body["role"] == ROLE_ANALYST
        assert body["org_id"] == str(org_id)
        assert "assigned_categories" in body

    async def test_me_org_field_populated_when_org_exists(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="me_user_2", role=ROLE_ORG_ADMIN, slug_suffix="me-b"
        )
        user = _make_user(
            user_id="me_user_2", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.get(
                "/v1/auth/me", headers={"Authorization": "Bearer t"}
            )
        assert r.status_code == 200
        body = r.json()
        assert body["organization"] is not None
        assert body["organization"]["id"] == str(org_id)

    async def test_platform_admin_has_null_org(
        self, client: AsyncClient
    ) -> None:
        from app.auth.base import ROLE_PLATFORM_ADMIN
        user = _make_user(role=ROLE_PLATFORM_ADMIN, org_id=None, clerk_org_id=None)
        with _patch_verifier(user):
            r = await client.get(
                "/v1/auth/me", headers={"Authorization": "Bearer t"}
            )
        assert r.status_code == 200
        body = r.json()
        assert body["role"] == ROLE_PLATFORM_ADMIN
        assert body["org_id"] is None
        assert body["organization"] is None


# ---------------------------------------------------------------------------
# D. Cross-tenant org access → 403
# ---------------------------------------------------------------------------

class TestCrossTenantOrgAccess:
    async def test_user_cannot_read_foreign_org(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        # Create two orgs
        org_a, _ = await _create_org_and_member(
            async_db, user_id="user_a", role=ROLE_ORG_USER, slug_suffix="ct-a"
        )
        org_b, _ = await _create_org_and_member(
            async_db, user_id="user_b", role=ROLE_ORG_USER, slug_suffix="ct-b"
        )

        # Authenticate as user_a (scoped to org_a) and try to read org_b
        user_a = _make_user(user_id="user_a", role=ROLE_ORG_USER, org_id=str(org_a))
        with _patch_verifier(user_a):
            r = await client.get(
                f"/v1/organizations/{org_b}",
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code in {403, 404}, (
            f"Expected 403 or 404 when reading a foreign org, got {r.status_code}"
        )

    async def test_user_cannot_patch_foreign_org(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_a, _ = await _create_org_and_member(
            async_db, user_id="admin_a", role=ROLE_ORG_ADMIN, slug_suffix="ct-patch-a"
        )
        org_b, _ = await _create_org_and_member(
            async_db, user_id="admin_b", role=ROLE_ORG_ADMIN, slug_suffix="ct-patch-b"
        )

        admin_a = _make_user(user_id="admin_a", role=ROLE_ORG_ADMIN, org_id=str(org_a))
        with _patch_verifier(admin_a):
            r = await client.patch(
                f"/v1/organizations/{org_b}",
                json={"name": "Hijacked"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code in {403, 404}

    async def test_user_cannot_list_members_of_foreign_org(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_a, _ = await _create_org_and_member(
            async_db, user_id="member_a", role=ROLE_ORG_USER, slug_suffix="ct-mem-a"
        )
        org_b, _ = await _create_org_and_member(
            async_db, user_id="member_b", role=ROLE_ORG_USER, slug_suffix="ct-mem-b"
        )

        user_a = _make_user(user_id="member_a", role=ROLE_ORG_USER, org_id=str(org_a))
        with _patch_verifier(user_a):
            r = await client.get(
                f"/v1/organizations/{org_b}/members",
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code in {403, 404}


# ---------------------------------------------------------------------------
# E. PATCH /v1/organizations/{id}
# ---------------------------------------------------------------------------

class TestPatchOrganization:
    async def test_org_admin_can_update_own_org(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="patch_admin", role=ROLE_ORG_ADMIN, slug_suffix="patch-e"
        )
        user = _make_user(
            user_id="patch_admin", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.patch(
                f"/v1/organizations/{org_id}",
                json={"name": "Updated Name"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Name"

    async def test_invalid_country_returns_422(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="patch_admin2", role=ROLE_ORG_ADMIN, slug_suffix="patch-422"
        )
        user = _make_user(
            user_id="patch_admin2", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.patch(
                f"/v1/organizations/{org_id}",
                json={"country": "TOOLONG"},  # must be 2-char
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 422
        body = r.json()
        # RFC 9457 shape
        assert body["status"] == 422
        assert "errors" in body


# ---------------------------------------------------------------------------
# F. GET /v1/organizations/{id}/members
# ---------------------------------------------------------------------------

class TestListMembers:
    async def test_org_user_can_list_members(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="list_member_user", role=ROLE_ORG_USER, slug_suffix="list-f"
        )
        user = _make_user(
            user_id="list_member_user", role=ROLE_ORG_USER, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.get(
                f"/v1/organizations/{org_id}/members",
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert "total" in body
        assert body["total"] >= 1

    async def test_read_only_can_list_members(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="ro_member", role=ROLE_READ_ONLY, slug_suffix="list-ro"
        )
        user = _make_user(
            user_id="ro_member", role=ROLE_READ_ONLY, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.get(
                f"/v1/organizations/{org_id}/members",
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# G. POST /v1/organizations/{id}/members
# ---------------------------------------------------------------------------

class TestInviteMembers:
    async def test_org_admin_can_invite_member(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="invite_admin", role=ROLE_ORG_ADMIN, slug_suffix="invite-g"
        )
        user = _make_user(
            user_id="invite_admin", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        new_user_id = f"new_user_{uuid.uuid4().hex[:8]}"
        with _patch_verifier(user):
            r = await client.post(
                f"/v1/organizations/{org_id}/members",
                json={"user_id": new_user_id, "role": "org_user"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 201
        body = r.json()
        assert body["user_id"] == new_user_id
        assert body["role"] == "org_user"

    async def test_cannot_invite_same_user_twice(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="invite_dupe_admin", role=ROLE_ORG_ADMIN, slug_suffix="invite-dupe"
        )
        user = _make_user(
            user_id="invite_dupe_admin", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        new_user_id = f"dupe_user_{uuid.uuid4().hex[:8]}"

        with _patch_verifier(user):
            # First invite
            r1 = await client.post(
                f"/v1/organizations/{org_id}/members",
                json={"user_id": new_user_id, "role": "org_user"},
                headers={"Authorization": "Bearer t"},
            )
            assert r1.status_code == 201

            # Second invite — same user
            r2 = await client.post(
                f"/v1/organizations/{org_id}/members",
                json={"user_id": new_user_id, "role": "org_user"},
                headers={"Authorization": "Bearer t"},
            )
        assert r2.status_code == 409

    async def test_invalid_role_returns_422(
        self, client: AsyncClient, async_db: AsyncSession
    ) -> None:
        org_id, _ = await _create_org_and_member(
            async_db, user_id="invite_bad_role", role=ROLE_ORG_ADMIN, slug_suffix="invite-badrole"
        )
        user = _make_user(
            user_id="invite_bad_role", role=ROLE_ORG_ADMIN, org_id=str(org_id)
        )
        with _patch_verifier(user):
            r = await client.post(
                f"/v1/organizations/{org_id}/members",
                json={"user_id": "some_user", "role": "superuser"},
                headers={"Authorization": "Bearer t"},
            )
        assert r.status_code == 422
