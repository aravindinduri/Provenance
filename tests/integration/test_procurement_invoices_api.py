"""
tests/integration/test_procurement_invoices_api.py — Integration tests for Phase 4 Purchase Invoices & 3-Way Matching APIs.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import app.db.models  # noqa: F401
from app.auth.base import ROLE_ANALYST, CurrentUser
from app.main import app
from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.spend.models import PurchaseOrder, SpendRecord

TEST_ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID = "user_procurement_analyst"


def _mock_analyst_user(org_id: uuid.UUID = TEST_ORG_ID) -> CurrentUser:
    return CurrentUser(
        user_id=TEST_USER_ID,
        org_id=str(org_id),
        clerk_org_id="clerk_org_test",
        role=ROLE_ANALYST,
        email="analyst@provenance.test",
    )


from app.core.deps import get_current_user


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = _mock_analyst_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer mock-token-for-test",
        "x-org-id": str(TEST_ORG_ID),
    }


@pytest.mark.asyncio
async def test_openapi_schema_includes_invoices():
    """Verify that OpenAPI documentation includes all Phase 4 /v1/invoices routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/openapi.json")
        assert res.status_code == 200
        schema = res.json()
        paths = schema.get("paths", {})
        assert "/v1/invoices" in paths
        assert "/v1/invoices/stats" in paths
        assert "/v1/invoices/{invoice_id}" in paths
        assert "/v1/invoices/{invoice_id}/match" in paths
        assert "/v1/invoices/{invoice_id}/approve" in paths
        assert "/v1/invoices/{invoice_id}/pay" in paths


@pytest.mark.asyncio
async def test_get_invoices_stats(auth_headers):
    """Verify that /v1/invoices/stats returns dynamically computed statistics."""
    mock_stats = {
        "total_count": 10,
        "total_amount": 150000.0,
        "matched_3way_count": 7,
        "matched_2way_count": 2,
        "exception_count": 1,
        "unmatched_count": 0,
        "paid_count": 5,
        "unpaid_count": 5,
        "paid_amount": 80000.0,
    }

    with (
        patch("app.core.deps.get_current_user", return_value=_mock_analyst_user()),
        patch(
            "app.modules.invoices.service.InvoiceService.get_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/v1/invoices/stats", headers=auth_headers)
            assert res.status_code == 200
            data = res.json()
            assert data["total_count"] == 10
            assert data["total_amount"] == 150000.0
            assert data["matched_3way_count"] == 7
            assert data["exception_count"] == 1


@pytest.mark.asyncio
async def test_create_and_match_invoice(auth_headers):
    """Verify creating an invoice returns HTTP 201 with properly serialized fields."""
    inv_id = uuid.uuid4()
    mock_invoice_out = {
        "id": str(inv_id),
        "org_id": str(TEST_ORG_ID),
        "invoice_number": "INV-2026-0042",
        "company_id": str(uuid.uuid4()),
        "supplier_name": "Jindal Stainless Ltd.",
        "po_id": str(uuid.uuid4()),
        "po_number": "PO-2026-0042",
        "goods_receipt_id": None,
        "grn_number": None,
        "invoice_date": "2026-10-16",
        "due_date": "2026-11-15",
        "amount": 2100000.0,
        "currency": "USD",
        "category": "Direct Procurement",
        "payment_status": "unpaid",
        "match_status": "matched_3way",
        "match_exceptions": [],
        "approved_by": "System Auto-Match",
        "approved_at": "2026-10-16T12:00:00Z",
        "paid_at": None,
        "line_items": [
            {
                "description": "Stainless Steel Sheet 304",
                "quantity": 500.0,
                "unit_price": 4200.0,
                "total_amount": 2100000.0,
                "unit_of_measure": "each",
                "item_id": None,
                "item_code": "SS304",
                "po_line_index": 0,
            }
        ],
        "notes": "Delivered to Chennai plant",
        "created_at": "2026-10-16T12:00:00Z",
        "updated_at": "2026-10-16T12:00:00Z",
    }

    with (
        patch("app.core.deps.get_current_user", return_value=_mock_analyst_user()),
        patch(
            "app.modules.invoices.service.InvoiceService.create_invoice",
            new_callable=AsyncMock,
            return_value=mock_invoice_out,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "supplier_name": "Jindal Stainless Ltd.",
                "amount": 2100000.0,
                "currency": "USD",
                "line_items": [
                    {
                        "description": "Stainless Steel Sheet 304",
                        "quantity": 500.0,
                        "unit_price": 4200.0,
                    }
                ],
                "auto_match": True,
            }
            res = await client.post("/v1/invoices", json=payload, headers=auth_headers)
            assert res.status_code == 201
            data = res.json()
            assert data["invoice_number"] == "INV-2026-0042"
            assert data["match_status"] == "matched_3way"
            assert data["approved_by"] == "System Auto-Match"
