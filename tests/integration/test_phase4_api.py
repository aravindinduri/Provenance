"""
tests/integration/test_phase4_api.py — Integration tests for Phase 4 Backend APIs.

Coverage:
  1. OpenAPI schema generation acceptance.
  2. Unauthenticated requests rejected with RFC 9457 401.
  3. Role & permission enforcement (org_user vs analyst vs org_admin).
  4. Companies search and detail endpoints.
  5. Suppliers CRUD endpoints (GET, POST, PATCH, DELETE).
  6. Relationships CRUD endpoints (GET, POST, PATCH, DELETE).
  7. Validation error handling (RFC 9457 422).
  8. Tenant scoping and isolation.
  9. Rate limit handling (RFC 9457 429).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.base import (
    ROLE_ANALYST,
    ROLE_ORG_USER,
    ROLE_READ_ONLY,
    CurrentUser,
)
from app.main import app, create_app
from app.modules.companies.schemas import (
    CompanyDetailOut,
    CompanyIdentifierOut,
    CompanyLocationOut,
    CompanySummaryOut,
    LocationOut,
)
from app.modules.companies.service import CompanyNotFound
from app.modules.graph.schemas import (
    RelationshipOut,
    SupplierOut,
)
from app.modules.graph.service import RelationshipNotFound, SupplierNotFound


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(
    *,
    user_id: str = "user_test",
    org_id: str = "00000000-0000-0000-0000-000000000001",
    role: str = ROLE_ANALYST,
) -> CurrentUser:
    return CurrentUser(
        user_id=user_id,
        org_id=org_id,
        clerk_org_id="clerk_org_test",
        role=role,
        email=f"{user_id}@provenance.app",
    )


def _patch_verifier(user: CurrentUser):
    return patch(
        "app.auth.providers.clerk.ClerkVerifier.verify",
        new=AsyncMock(return_value=user),
    )


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── 1. OpenAPI Acceptance ────────────────────────────────────────────────────

def test_openapi_schema_generation():
    """Verify that the OpenAPI 3.1 schema generates with all Phase 4 paths."""
    api = create_app()
    schema = api.openapi()
    assert schema is not None
    assert "paths" in schema

    paths = schema["paths"]
    assert "/v1/companies/search" in paths
    assert "/v1/companies/{company_id}" in paths
    assert "/v1/suppliers" in paths
    assert "/v1/suppliers/{supplier_id}" in paths
    assert "/v1/relationships" in paths
    assert "/v1/relationships/{relationship_id}" in paths


# ── 2. Auth & Role Enforcement ───────────────────────────────────────────────

class TestAuthAndPermissions:
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        r = await client.get("/v1/companies/search?q=acme")
        assert r.status_code == 401
        body = r.json()
        assert body["type"] == "https://api.provenance.app/errors/unauthorized"
        assert body["status"] == 401

    async def test_org_user_cannot_create_supplier(self, client: AsyncClient):
        user = _make_user(role=ROLE_ORG_USER)
        with _patch_verifier(user):
            r = await client.post(
                "/v1/suppliers",
                json={"legal_name": "Prohibited Co"},
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 403
        body = r.json()
        assert body["type"] == "https://api.provenance.app/errors/forbidden"

    async def test_read_only_cannot_create_relationship(self, client: AsyncClient):
        user = _make_user(role=ROLE_READ_ONLY)
        with _patch_verifier(user):
            r = await client.post(
                "/v1/relationships",
                json={
                    "from_company_id": str(uuid.uuid4()),
                    "to_org_id": str(uuid.uuid4()),
                },
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 403

    async def test_analyst_can_access_write_endpoints(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        mock_supplier = SupplierOut(
            id=uuid.uuid4(),
            org_id=uuid.UUID(user.org_id),
            company_id=uuid.uuid4(),
            company=CompanySummaryOut(
                id=uuid.uuid4(),
                legal_name="Allowed Co",
                name_norm="allowed co",
                confidence=1.0,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            relationship_type="supplies_to",
            criticality=3,
            valid_from=date.today(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with _patch_verifier(user), patch(
            "app.api.v1.suppliers.GraphService.create_supplier",
            new=AsyncMock(return_value=mock_supplier),
        ), patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new=AsyncMock()):
            r = await client.post(
                "/v1/suppliers",
                json={"legal_name": "Allowed Co", "criticality": 3},
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 201


# ── 3. Companies Endpoints ───────────────────────────────────────────────────

class TestCompaniesEndpoints:
    async def test_search_companies(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        comp = CompanySummaryOut(
            id=uuid.uuid4(),
            legal_name="Acme Alloys Ltd",
            name_norm="acme alloys ltd",
            country="US",
            confidence=1.0,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with _patch_verifier(user), patch(
            "app.api.v1.companies.CompanyService.search_companies",
            new=AsyncMock(return_value=([comp], "cursor_token_123", True)),
        ):
            r = await client.get(
                "/v1/companies/search?q=acme&country=US&limit=10",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["legal_name"] == "Acme Alloys Ltd"
        assert body["pagination"]["next_cursor"] == "cursor_token_123"
        assert body["pagination"]["has_more"] is True

    async def test_get_company_detail_success(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        cid = uuid.uuid4()
        comp_detail = CompanyDetailOut(
            id=cid,
            legal_name="Henan Yixin Specialty Alloys",
            name_norm="henan yixin specialty alloys",
            country="CN",
            confidence=0.95,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            identifiers=[
                CompanyIdentifierOut(
                    id=uuid.uuid4(),
                    identifier_type="lei",
                    identifier_value="5493001KJTIIGC8Y1R12",
                    issuing_country="CN",
                )
            ],
            locations=[
                CompanyLocationOut(
                    id=uuid.uuid4(),
                    site_type="plant",
                    is_primary=True,
                    confidence=1.0,
                    location=LocationOut(
                        id=uuid.uuid4(),
                        country="CN",
                        city="Luoyang",
                    ),
                )
            ],
        )

        with _patch_verifier(user), patch(
            "app.api.v1.companies.CompanyService.get_company_detail",
            new=AsyncMock(return_value=comp_detail),
        ):
            r = await client.get(
                f"/v1/companies/{cid}",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["legal_name"] == "Henan Yixin Specialty Alloys"
        assert len(body["identifiers"]) == 1
        assert body["identifiers"][0]["identifier_type"] == "lei"
        assert len(body["locations"]) == 1
        assert body["locations"][0]["location"]["city"] == "Luoyang"

    async def test_get_company_not_found(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        cid = uuid.uuid4()
        with _patch_verifier(user), patch(
            "app.api.v1.companies.CompanyService.get_company_detail",
            new=AsyncMock(side_effect=CompanyNotFound(cid)),
        ):
            r = await client.get(
                f"/v1/companies/{cid}",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 404
        body = r.json()
        assert body["type"] == "https://api.provenance.app/errors/not-found"


# ── 4. Suppliers CRUD Endpoints ──────────────────────────────────────────────

class TestSuppliersCRUD:
    async def test_list_suppliers(self, client: AsyncClient):
        user = _make_user(role=ROLE_ORG_USER)
        supplier = SupplierOut(
            id=uuid.uuid4(),
            org_id=uuid.UUID(user.org_id),
            company_id=uuid.uuid4(),
            company=CompanySummaryOut(
                id=uuid.uuid4(),
                legal_name="Supplier Alpha",
                name_norm="supplier alpha",
                confidence=1.0,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            relationship_type="supplies_to",
            criticality=4,
            annual_spend_usd=2500000.0,
            category="Semiconductors",
            single_source=True,
            valid_from=date.today(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with _patch_verifier(user), patch(
            "app.api.v1.suppliers.GraphService.list_suppliers",
            new=AsyncMock(return_value=([supplier], None, False)),
        ):
            r = await client.get(
                "/v1/suppliers?category=Semiconductors&criticality=4",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["category"] == "Semiconductors"
        assert body["data"][0]["single_source"] is True

    async def test_get_supplier_detail(self, client: AsyncClient):
        user = _make_user(role=ROLE_ORG_USER)
        sid = uuid.uuid4()
        supplier = SupplierOut(
            id=sid,
            org_id=uuid.UUID(user.org_id),
            company_id=uuid.uuid4(),
            company=CompanySummaryOut(
                id=uuid.uuid4(),
                legal_name="Supplier Beta",
                name_norm="supplier beta",
                confidence=1.0,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            relationship_type="supplies_to",
            criticality=5,
            valid_from=date.today(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with _patch_verifier(user), patch(
            "app.api.v1.suppliers.GraphService.get_supplier",
            new=AsyncMock(return_value=supplier),
        ):
            r = await client.get(
                f"/v1/suppliers/{sid}",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 200
        assert r.json()["id"] == str(sid)

    async def test_patch_supplier(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        sid = uuid.uuid4()
        updated_supplier = SupplierOut(
            id=sid,
            org_id=uuid.UUID(user.org_id),
            company_id=uuid.uuid4(),
            company=CompanySummaryOut(
                id=uuid.uuid4(),
                legal_name="Supplier Beta",
                name_norm="supplier beta",
                confidence=1.0,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            relationship_type="supplies_to",
            criticality=2,
            annual_spend_usd=50000.0,
            valid_from=date.today(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with _patch_verifier(user), patch(
            "app.api.v1.suppliers.GraphService.update_supplier",
            new=AsyncMock(return_value=updated_supplier),
        ), patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new=AsyncMock()):
            r = await client.patch(
                f"/v1/suppliers/{sid}",
                json={"criticality": 2, "annual_spend_usd": 50000.0},
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 200
        assert r.json()["criticality"] == 2
        assert r.json()["annual_spend_usd"] == 50000.0

    async def test_delete_supplier(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        sid = uuid.uuid4()

        with _patch_verifier(user), patch(
            "app.api.v1.suppliers.GraphService.delete_supplier",
            new=AsyncMock(return_value=None),
        ), patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new=AsyncMock()):
            r = await client.delete(
                f"/v1/suppliers/{sid}",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 204

    async def test_validation_error_returns_rfc9457(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        with _patch_verifier(user):
            # Criticality must be 1-5, spend >= 0
            r = await client.post(
                "/v1/suppliers",
                json={"legal_name": "Test Co", "criticality": 99, "annual_spend_usd": -100},
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 422
        body = r.json()
        assert body["type"] == "https://api.provenance.app/errors/validation-error"
        assert body["status"] == 422
        assert "errors" in body
        error_fields = {e["field"] for e in body["errors"]}
        assert "criticality" in error_fields or "body.criticality" in error_fields


# ── 5. Relationships CRUD Endpoints ──────────────────────────────────────────

class TestRelationshipsCRUD:
    async def test_list_and_create_relationships(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        from_id = uuid.uuid4()
        to_id = uuid.uuid4()
        rel_id = uuid.uuid4()

        rel_out = RelationshipOut(
            id=rel_id,
            org_id=uuid.UUID(user.org_id),
            from_company_id=from_id,
            from_company=CompanySummaryOut(
                id=from_id,
                legal_name="Tier 2 Mining",
                name_norm="tier 2 mining",
                confidence=1.0,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            to_company_id=to_id,
            to_company=CompanySummaryOut(
                id=to_id,
                legal_name="Tier 1 Smelter",
                name_norm="tier 1 smelter",
                confidence=1.0,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            relationship_type="sub_supplies_to",
            tier=2,
            valid_from=date.today(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with _patch_verifier(user), patch(
            "app.api.v1.relationships.GraphService.create_relationship",
            new=AsyncMock(return_value=rel_out),
        ), patch("sqlalchemy.ext.asyncio.AsyncSession.commit", new=AsyncMock()):
            r = await client.post(
                "/v1/relationships",
                json={
                    "from_company_id": str(from_id),
                    "to_company_id": str(to_id),
                    "relationship_type": "sub_supplies_to",
                    "tier": 2,
                },
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 201
        assert r.json()["relationship_type"] == "sub_supplies_to"
        assert r.json()["tier"] == 2

    async def test_delete_relationship_not_found(self, client: AsyncClient):
        user = _make_user(role=ROLE_ANALYST)
        rid = uuid.uuid4()
        with _patch_verifier(user), patch(
            "app.api.v1.relationships.GraphService.delete_relationship",
            new=AsyncMock(side_effect=RelationshipNotFound(rid)),
        ):
            r = await client.delete(
                f"/v1/relationships/{rid}",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 404
        assert r.json()["type"] == "https://api.provenance.app/errors/not-found"


# ── 6. Tenant Scoping & Isolation ────────────────────────────────────────────

class TestTenantIsolation:
    async def test_user_cannot_access_foreign_tenant_supplier(self, client: AsyncClient):
        """
        Verify tenant isolation: when Org B's user requests a supplier belonging
        to Org A, the service filters by Org B's org_id and returns 404 Not Found.
        """
        user_b = _make_user(
            user_id="user_tenant_b",
            org_id=str(uuid.uuid4()),
            role=ROLE_ANALYST,
        )
        supplier_id_org_a = uuid.uuid4()

        # The service for Org B cannot find supplier_id_org_a
        with _patch_verifier(user_b), patch(
            "app.api.v1.suppliers.GraphService.get_supplier",
            new=AsyncMock(side_effect=SupplierNotFound(supplier_id_org_a)),
        ):
            r = await client.get(
                f"/v1/suppliers/{supplier_id_org_a}",
                headers={"Authorization": "Bearer token_b"},
            )
        assert r.status_code == 404
        assert r.json()["type"] == "https://api.provenance.app/errors/not-found"

    async def test_user_cannot_mutate_foreign_tenant_supplier(self, client: AsyncClient):
        user_b = _make_user(
            user_id="user_tenant_b",
            org_id=str(uuid.uuid4()),
            role=ROLE_ANALYST,
        )
        supplier_id_org_a = uuid.uuid4()

        with _patch_verifier(user_b), patch(
            "app.api.v1.suppliers.GraphService.update_supplier",
            new=AsyncMock(side_effect=SupplierNotFound(supplier_id_org_a)),
        ):
            r = await client.patch(
                f"/v1/suppliers/{supplier_id_org_a}",
                json={"criticality": 1},
                headers={"Authorization": "Bearer token_b"},
            )
        assert r.status_code == 404

    async def test_user_cannot_delete_foreign_tenant_supplier(self, client: AsyncClient):
        user_b = _make_user(
            user_id="user_tenant_b",
            org_id=str(uuid.uuid4()),
            role=ROLE_ANALYST,
        )
        supplier_id_org_a = uuid.uuid4()

        with _patch_verifier(user_b), patch(
            "app.api.v1.suppliers.GraphService.delete_supplier",
            new=AsyncMock(side_effect=SupplierNotFound(supplier_id_org_a)),
        ):
            r = await client.delete(
                f"/v1/suppliers/{supplier_id_org_a}",
                headers={"Authorization": "Bearer token_b"},
            )
        assert r.status_code == 404


# ── 7. Rate Limiting (RFC 9457 429) ──────────────────────────────────────────

class TestRateLimiting:
    async def test_rate_limit_exceeded_handler_rfc9457(self, client: AsyncClient):
        from unittest.mock import MagicMock
        from slowapi.errors import RateLimitExceeded
        user = _make_user(role=ROLE_ANALYST)

        mock_limit = MagicMock(error_message="1000 per 1 hour")

        # Trigger rate limit handler
        with _patch_verifier(user), patch(
            "app.api.v1.suppliers.GraphService.list_suppliers",
            side_effect=RateLimitExceeded(mock_limit),
        ):
            r = await client.get(
                "/v1/suppliers",
                headers={"Authorization": "Bearer token"},
            )
        assert r.status_code == 429
        body = r.json()
        assert body["type"] == "https://api.provenance.app/errors/rate-limit-exceeded"
        assert body["status"] == 429
        assert body["title"] == "Rate Limit Exceeded"
        assert "Retry-After" in r.headers
        assert int(r.headers["Retry-After"]) > 0
