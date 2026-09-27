"""
Phase 1 acceptance test: GET /health returns 200.

This is the minimal check that the app factory, config, and router wire up
correctly. It runs without a real database or Redis (liveness only).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_liveness() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body


@pytest.mark.asyncio
async def test_readiness_degraded_without_db() -> None:
    """
    In unit-test context there is no real DB or Redis.
    /health/ready must return 503 (not 500 — the endpoint handles the error).
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    # 503 is the correct response when dependencies are unavailable
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert "database" in body["checks"]
