"""
tests/unit/test_phase6_alerts.py — Unit tests for Phase 6 Alert schemas, action validation, and count structures.
"""

import uuid
from app.modules.alerts.schemas import (
    AlertActionCreate,
    AlertCountsOut,
    AlertEvidenceOut,
    AlertOut,
    AlertScanResponse,
    PaginatedAlerts,
)


def test_alert_action_create_schema():
    action = AlertActionCreate(action="acknowledged", note="Reviewing with compliance team")
    assert action.action == "acknowledged"
    assert action.note == "Reviewing with compliance team"


def test_alert_counts_out_defaults():
    counts = AlertCountsOut()
    assert counts.total == 0
    assert counts.critical == 0
    assert counts.new == 0
    assert counts.investigating == 0
    assert counts.resolved == 0


def test_paginated_alerts_schema():
    aid = uuid.uuid4()
    org_id = uuid.uuid4()
    alert_out = AlertOut(
        id=aid,
        org_id=org_id,
        risk_assessment_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        headline="Semiconductor Export Control Notice",
        severity_band="CRITICAL",
        impact_score=85.0,
        confidence=0.92,
        status="new",
        created_at="2026-10-10T12:00:00Z",
        updated_at="2026-10-10T12:00:00Z",
        company_name="Tokyo Electron Ltd",
    )
    paginated = PaginatedAlerts(data=[alert_out], total=1, limit=50, offset=0)
    assert paginated.total == 1
    assert paginated.data[0].id == aid
    assert paginated.data[0].company_name == "Tokyo Electron Ltd"
    assert paginated.data[0].severity_band == "CRITICAL"


def test_alert_scan_response():
    resp = AlertScanResponse(
        scanned_suppliers=5,
        generated_alerts=2,
        message="Scan completed successfully",
    )
    assert resp.scanned_suppliers == 5
    assert resp.generated_alerts == 2
