"""
/v1/alerts — Supply-chain risk alerts and signal stream management.

Endpoints:
  GET    /alerts              — list tenant's alerts with faceted filters & search
  GET    /alerts/counts       — summary counts by status & severity
  GET    /alerts/{id}         — get single alert with full evidence chain & audit actions
  POST   /alerts/{id}/actions — record action (acknowledge, investigate, escalate, dismiss, resolve)
  POST   /alerts/scan         — run risk scan over tenant's suppliers
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import bad_request, not_found
from app.db.session import get_db
from app.modules.alerts.schemas import (
    AlertActionCreate,
    AlertCountsOut,
    AlertOut,
    AlertScanResponse,
    PaginatedAlerts,
)
from app.modules.alerts.service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _service(db: AsyncSession) -> AlertService:
    return AlertService(db)


def _get_org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise bad_request("Tenant organization context (org_id) is required for alert operations")
    return uuid.UUID(current_user.org_id)


@router.get("", response_model=PaginatedAlerts)
async def list_alerts(
    current_user: Annotated[CurrentUser, Depends(require_permission("alerts:read"))],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    severity: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    company_id: Annotated[uuid.UUID | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
) -> PaginatedAlerts:
    """List tenant's alerts with faceted filtering, search, and pagination."""
    org_id = _get_org_id(current_user)
    service = _service(db)
    return await service.list_alerts(
        org_id=org_id,
        status=status_filter,
        severity=severity,
        category=category,
        company_id=company_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/counts", response_model=AlertCountsOut)
async def get_alert_counts(
    current_user: Annotated[CurrentUser, Depends(require_permission("alerts:read"))],
    db: AsyncSession = Depends(get_db),
) -> AlertCountsOut:
    """Get count metrics of alerts by severity and status for the current tenant."""
    org_id = _get_org_id(current_user)
    service = _service(db)
    return await service.get_counts(org_id=org_id)


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission("alerts:read"))],
    db: AsyncSession = Depends(get_db),
) -> AlertOut:
    """Retrieve full details, evidence items, and action history for an alert."""
    org_id = _get_org_id(current_user)
    service = _service(db)
    alert = await service.get_alert(org_id=org_id, alert_id=alert_id)
    if not alert:
        raise not_found(f"Alert {alert_id} not found in this organization")
    return alert


@router.post("/{alert_id}/actions", response_model=AlertOut)
async def record_alert_action(
    alert_id: uuid.UUID,
    payload: AlertActionCreate,
    current_user: Annotated[CurrentUser, Depends(require_permission("alerts:write"))],
    db: AsyncSession = Depends(get_db),
) -> AlertOut:
    """
    Take action on an alert (acknowledged, investigating, escalated, dismissed, resolved).
    Records an immutable audit action in alert_actions.
    """
    org_id = _get_org_id(current_user)
    service = _service(db)

    allowed = {"acknowledged", "investigating", "escalated", "dismissed", "resolved"}
    if payload.action.lower() not in allowed:
        raise bad_request(f"Invalid action '{payload.action}'. Must be one of: {', '.join(allowed)}")

    updated = await service.record_action(
        org_id=org_id,
        alert_id=alert_id,
        user_id=current_user.user_id,
        action=payload.action,
        note=payload.note,
    )
    if not updated:
        raise not_found(f"Alert {alert_id} not found")
    return updated


@router.post("/scan", response_model=AlertScanResponse, status_code=status.HTTP_200_OK)
async def run_risk_scan(
    current_user: Annotated[CurrentUser, Depends(require_permission("alerts:write"))],
    db: AsyncSession = Depends(get_db),
) -> AlertScanResponse:
    """
    Runs a live risk scan across the tenant's registered suppliers.
    Cross-checks regulatory, sanctions, and supply chain indicators to generate authentic alerts.
    """
    org_id = _get_org_id(current_user)
    service = _service(db)
    return await service.run_risk_scan(org_id=org_id, user_id=current_user.user_id)
