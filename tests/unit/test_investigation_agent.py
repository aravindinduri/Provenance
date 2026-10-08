"""
tests/unit/test_investigation_agent.py — Unit tests for AI Investigation Agent (Agent 4).
Tests tenant-scoped graph traversal, signal correlation, trace steps, and Gemini structured synthesis.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import DefaultClause

sqlite3.register_adapter(list, json.dumps)
sqlite3.register_adapter(dict, json.dumps)

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(DefaultClause, "sqlite")
def compile_default_sqlite(element, compiler, **kw):
    return ""

import app.modules.organizations.models  # Ensure organizations table is loaded for foreign keys
import app.modules.events.models         # Ensure source_records table is loaded for foreign keys

from app.modules.ai.gateway import LLMGateway
from app.modules.ai.investigation.schemas import (
    InvestigationQueryRequest,
    InvestigationSynthesisOutput,
)
from app.modules.ai.investigation.service import InvestigationAgentService
from app.modules.ai.provider import MockProvider
from app.modules.companies.models import Company
from app.modules.events.models import Event
from app.modules.graph.models import SupplierRelationship


class AsyncTestSessionAdapter:
    def __init__(self, sync_session):
        self._s = sync_session

    async def execute(self, statement, *args, **kwargs):
        return self._s.execute(statement, *args, **kwargs)

    def add(self, instance):
        self._s.add(instance)

    async def flush(self):
        self._s.flush()

    async def commit(self):
        self._s.commit()

    async def rollback(self):
        self._s.rollback()


@pytest.fixture
def sqlite_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    tables = [
        """
        CREATE TABLE organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE companies (
            id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            name_norm TEXT NOT NULL,
            country TEXT,
            jurisdiction TEXT,
            legal_form TEXT,
            entity_status TEXT,
            primary_domain TEXT,
            industry_codes TEXT DEFAULT '[]',
            registered_address TEXT,
            hq_address TEXT,
            data_source TEXT,
            enrichment_status TEXT DEFAULT 'pending',
            last_enriched_at TIMESTAMP,
            confidence REAL DEFAULT 1.0,
            is_verified BOOLEAN DEFAULT 0,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
        """,
        """
        CREATE TABLE supplier_relationships (
            id TEXT PRIMARY KEY,
            org_id TEXT NOT NULL,
            from_company_id TEXT NOT NULL REFERENCES companies(id),
            to_company_id TEXT REFERENCES companies(id),
            to_org_id TEXT,
            relationship_type TEXT NOT NULL,
            tier INTEGER,
            criticality INTEGER,
            annual_spend_usd REAL,
            category TEXT,
            single_source BOOLEAN DEFAULT 0,
            lead_time_days INTEGER,
            confidence REAL DEFAULT 1.0,
            source TEXT,
            source_record_id TEXT,
            valid_from DATE,
            valid_to DATE,
            verified_at TIMESTAMP,
            verified_by TEXT,
            inherited_from_edge_id TEXT,
            deleted_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
        """,
        """
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            event_cluster_key TEXT NOT NULL,
            event_type TEXT NOT NULL,
            jurisdictions TEXT DEFAULT '[]',
            affected_materials TEXT DEFAULT '[]',
            affected_hs_codes TEXT DEFAULT '[]',
            effective_date DATE,
            expiry_date DATE,
            published_date DATE,
            summary TEXT NOT NULL,
            severity_signal TEXT,
            confidence INTEGER,
            corroboration_count INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            superseded_by TEXT,
            extracted_by_model TEXT,
            prompt_version TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
        """,
        """
        CREATE TABLE agent_runs (
            id TEXT PRIMARY KEY,
            org_id TEXT,
            agent_name TEXT NOT NULL,
            workflow_run_id TEXT,
            input_ref TEXT,
            output_ref TEXT,
            model TEXT,
            prompt_version TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            cost_usd REAL,
            latency_ms INTEGER,
            status TEXT,
            error TEXT,
            langfuse_trace_id TEXT,
            created_at TIMESTAMP
        )
        """,
    ]
    with engine.connect() as conn:
        for tbl in tables:
            conn.execute(text(tbl))
        conn.commit()

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield AsyncTestSessionAdapter(session)
    finally:
        session.close()


@pytest.mark.asyncio
async def test_investigation_agent_end_to_end(sqlite_db_session):
    """Test full conversational investigation with tenant graph and mock LLM response."""
    org_id = uuid.uuid4()

    # Seed supplier in Taiwan
    comp_id = uuid.uuid4()
    comp = Company(
        id=comp_id,
        legal_name="TSMC Sub-Tier Packaging Ltd",
        name_norm="tsmc sub-tier packaging",
        country="TW",
        primary_domain="tsmc-packaging.com",
    )
    sqlite_db_session.add(comp)

    rel = SupplierRelationship(
        id=uuid.uuid4(),
        org_id=org_id,
        from_company_id=comp_id,
        relationship_type="supplier_to",
        tier=1,
        criticality=5,
        annual_spend_usd=4500000.0,
        category="Semiconductors",
        source="manual",
    )
    sqlite_db_session.add(rel)

    # Seed external regulatory event
    event = Event(
        id=uuid.uuid4(),
        event_cluster_key="cluster_tw_export_2026",
        event_type="trade_restriction",
        jurisdictions=["TW", "CN"],
        affected_materials=["Silicon", "Gallium Arsenide"],
        summary="Export licensing review initiated on high-precision semiconductor assembly tools.",
        severity_signal="high",
        confidence=95,
        status="active",
    )
    sqlite_db_session.add(event)
    await sqlite_db_session.commit()

    # Configure MockProvider for synthesis
    mock_provider = MockProvider()
    mock_provider.add_response(
        InvestigationSynthesisOutput(
            summary="Tenant maintains critical single-source exposure to Taiwan via TSMC Sub-Tier Packaging ($4.5M spend).",
            detailed_analysis="### Taiwan Supply Chain Risk\nTSMC Packaging operates in an active export licensing review zone.",
            risk_level="high",
            key_findings=[
                "High dependency on Taiwan ($4.5M annual spend)",
                "Tier-1 criticality 5 node directly affected",
            ],
            recommended_actions=[
                "Establish dual-sourcing pre-qualification in alternative regions (e.g. EU or US).",
                "Audit tier-2 wafer suppliers for potential cross-choke points.",
            ],
        )
    )

    gateway = LLMGateway(db=sqlite_db_session, provider=mock_provider)
    service = InvestigationAgentService(db=sqlite_db_session, gateway=gateway)

    req = InvestigationQueryRequest(query="Which suppliers are exposed to Taiwan export restrictions?")
    res = await service.investigate(req, org_id=org_id)

    # Assertions
    assert res.query == "Which suppliers are exposed to Taiwan export restrictions?"
    assert res.risk_level == "high"
    assert "TSMC Sub-Tier Packaging" in res.summary
    assert len(res.recommended_actions) == 2
    assert len(res.execution_trace) == 4

    # Verify trace steps
    step_ids = [s.step_id for s in res.execution_trace]
    assert step_ids == ["step_intent", "step_graph", "step_signals", "step_synthesis"]

    # Verify citations include the supplier and event
    citation_types = [c.citation_type for c in res.citations]
    assert "supplier" in citation_types
    assert "event" in citation_types


@pytest.mark.asyncio
async def test_investigation_agent_tenant_isolation(sqlite_db_session):
    """Verify that investigation only scans suppliers for the caller's org_id."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    comp_a = Company(
        id=uuid.uuid4(),
        legal_name="Org A Secret Supplier",
        name_norm="org a secret supplier",
        country="DE",
    )
    sqlite_db_session.add(comp_a)
    sqlite_db_session.add(
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_a,
            from_company_id=comp_a.id,
            relationship_type="supplier_to",
            criticality=5,
        )
    )

    comp_b = Company(
        id=uuid.uuid4(),
        legal_name="Org B Supplier",
        name_norm="org b supplier",
        country="JP",
    )
    sqlite_db_session.add(comp_b)
    sqlite_db_session.add(
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_b,
            from_company_id=comp_b.id,
            relationship_type="supplier_to",
            criticality=2,
        )
    )
    await sqlite_db_session.commit()

    mock_provider = MockProvider()
    gateway = LLMGateway(db=sqlite_db_session, provider=mock_provider)
    service = InvestigationAgentService(db=sqlite_db_session, gateway=gateway)

    # Inquire as Org B
    req = InvestigationQueryRequest(query="List all my suppliers")
    res = await service.investigate(req, org_id=org_b)

    # Supplier A must NOT appear in Org B's citations
    citation_titles = [c.title for c in res.citations]
    assert "Org B Supplier" in citation_titles
    assert "Org A Secret Supplier" not in citation_titles


@pytest.mark.asyncio
async def test_investigation_suggestions(sqlite_db_session):
    """Verify context-aware starter query suggestions."""
    org_id = uuid.uuid4()
    comp = Company(
        id=uuid.uuid4(),
        legal_name="Samsung Heavy",
        name_norm="samsung heavy",
        country="KR",
    )
    sqlite_db_session.add(comp)
    sqlite_db_session.add(
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=comp.id,
            relationship_type="supplier_to",
        )
    )
    await sqlite_db_session.commit()

    service = InvestigationAgentService(db=sqlite_db_session, gateway=AsyncMock())
    suggestions = await service.get_suggestions(org_id=org_id)

    assert len(suggestions) >= 4
    assert any("KR" in s.prompt or "Korea" in s.title or "Geopolitical" in s.title for s in suggestions)
