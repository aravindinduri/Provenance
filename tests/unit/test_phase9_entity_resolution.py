"""
tests/unit/test_phase9_entity_resolution.py — Comprehensive test suite for Phase 9:
Entity resolution cascade (Stages 0-7), normalization, deterministic stages 1-5,
interchangeable AI providers (Gemini default, Claude, OpenAI, Mock), LLMGateway,
Stage 6 AI adjudication agent + guardrails, Stage 7 review queue & APIs,
GLEIF hierarchy enrichment seeding owned_by edges,
and the 150-pair evaluation dataset (precision >= 95%, recall >= 85%, >= 80% resolved before Stage 6,
and hard negatives MUST NOT merge).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import DefaultClause

sqlite3.register_adapter(list, json.dumps)
sqlite3.register_adapter(dict, json.dumps)

from app.config import get_settings
from app.db.base import Base

# Compile PostgreSQL types for SQLite in-memory test runner
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
from app.modules.ai.provider import (
    BaseAIProvider,
    ClaudeProvider,
    GeminiProvider,
    MockProvider,
    OpenAIProvider,
    get_ai_provider,
)
from app.modules.companies.gleif_enrichment import GleifEnrichmentService
from app.modules.companies.models import (
    Company,
    CompanyAlias,
    CompanyIdentifier,
    EntityResolutionReview,
)
from app.modules.companies.normalizer import (
    is_free_mail_domain,
    normalize_company_name,
    normalize_domain,
    normalize_for_resolution,
)
from app.modules.companies.resolution.cascade import (
    EntityResolutionCascade,
    token_similarity,
)
from app.modules.companies.schemas import (
    CandidateMatchOut,
    EntityResolveRequest,
    EntityResolveResponse,
    Stage6AdjudicationOut,
)
from app.modules.graph.models import SupplierRelationship


# ── SQLite In-Memory Async Session Adapter for Tests ────────────────────────

class AsyncTestSessionAdapter:
    """Lightweight async wrapper over synchronous SQLite session for testing."""

    def __init__(self, sync_session: Session) -> None:
        self._s = sync_session

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return self._s.execute(statement, *args, **kwargs)

    def add(self, instance: Any) -> None:
        self._s.add(instance)

    async def flush(self) -> None:
        self._s.flush()

    async def commit(self) -> None:
        self._s.commit()

    async def rollback(self) -> None:
        self._s.rollback()


@pytest.fixture
def sqlite_db_session():
    """In-memory SQLite DB with explicit SQLite-compatible DDL."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    tables = [
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
        CREATE TABLE company_identifiers (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL REFERENCES companies(id),
            identifier_type TEXT NOT NULL,
            identifier_value TEXT NOT NULL,
            issuing_country TEXT,
            source TEXT,
            verified_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
        """,
        """
        CREATE TABLE company_aliases (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL REFERENCES companies(id),
            alias TEXT NOT NULL,
            alias_norm TEXT NOT NULL,
            alias_type TEXT,
            source TEXT,
            confidence REAL,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
        """,
        """
        CREATE TABLE entity_resolution_reviews (
            id TEXT PRIMARY KEY,
            org_id TEXT,
            raw_name TEXT NOT NULL,
            context TEXT DEFAULT '{}',
            candidates TEXT DEFAULT '[]',
            suggested_company_id TEXT REFERENCES companies(id),
            ai_confidence REAL,
            ai_reasoning TEXT,
            status TEXT DEFAULT 'pending',
            resolved_company_id TEXT REFERENCES companies(id),
            resolved_by TEXT,
            resolved_at TIMESTAMP,
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


# ── 1. Stage 0 Normalization Tests ──────────────────────────────────────────

def test_stage0_legal_suffix_stripping():
    """Tests that common corporate legal suffixes are stripped cleanly for ER."""
    assert normalize_for_resolution("Microsoft Corporation") == "microsoft"
    assert normalize_for_resolution("Microsoft Corp.") == "microsoft"
    assert normalize_for_resolution("Acme Holdings LLC") == "acme"
    assert normalize_for_resolution("Siemens AG") == "siemens"
    assert normalize_for_resolution("Tata Motors Limited") == "tata motors"
    assert normalize_for_resolution("Reliance Industries Pvt. Ltd.") == "reliance industries"
    assert normalize_for_resolution("Bavarian Fasteners GmbH") == "bavarian fasteners"
    assert normalize_for_resolution("Toyota Motor Co., Ltd.") == "toyota motor"


def test_stage0_unicode_and_punctuation():
    """Tests unicode transliteration and punctuation removal."""
    assert normalize_for_resolution("Société Générale S.A.") == "societe generale"
    assert normalize_for_resolution("Héñàn Yíxìn Àllòys Cò.") == "henan yixin alloys"
    assert normalize_for_resolution("Foxconn Technology Group / Hon Hai") == "foxconn technology group hon hai"


def test_stage0_domain_normalization_and_free_mail_blocking():
    """Tests domain normalization and free-mail rejection (Stage 2)."""
    assert normalize_domain("https://www.apple.com/iphone") == "apple.com"
    assert normalize_domain("HTTP://WWW.MICROSOFT.COM:8080/test") == "microsoft.com"
    assert normalize_domain("siemens.de") == "siemens.de"

    # Free-mail domains must be rejected
    assert is_free_mail_domain("gmail.com") is True
    assert is_free_mail_domain("user@yahoo.co.uk") is True
    assert is_free_mail_domain("contact@outlook.com") is True
    assert is_free_mail_domain("apple.com") is False
    assert is_free_mail_domain("siemens.com") is False


# ── 2. AI Provider Interchangeability (Gemini Default, Zero Vendor Lock-in) ──

def test_ai_provider_factory_defaults_to_gemini():
    """The default AI provider must be Google Gemini per architectural requirements."""
    settings = get_settings()
    assert settings.llm_provider == "gemini"
    provider = get_ai_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"


def test_ai_provider_factory_interchangeable():
    """AI services must be easily interchangeable between Gemini, Claude, OpenAI, and Mock."""
    p_gemini = get_ai_provider("gemini")
    assert isinstance(p_gemini, GeminiProvider)

    p_claude = get_ai_provider("anthropic")
    assert isinstance(p_claude, ClaudeProvider)

    p_openai = get_ai_provider("openai")
    assert isinstance(p_openai, OpenAIProvider)

    p_mock = get_ai_provider("mock")
    assert isinstance(p_mock, MockProvider)


@pytest.mark.asyncio
async def test_llm_gateway_structured_execution_with_mock_and_caching(sqlite_db_session):
    """Test LLMGateway executes structured output and caches identical calls."""
    mock_provider = MockProvider()
    mock_provider.add_response({
        "decision": "match",
        "company_id": str(uuid.uuid4()),
        "confidence": 0.92,
        "reasoning": "Candidate matches legal entity hierarchy.",
        "evidence_fields": ["legal_name", "country"],
    })

    gateway = LLMGateway(db=sqlite_db_session, provider=mock_provider)
    result = await gateway.execute_structured(
        task="entity_resolution",
        prompt="Adjudicate mention",
        schema=Stage6AdjudicationOut,
        use_cache=True,
    )

    assert result.decision == "match"
    assert result.confidence == 0.92
    assert "hierarchy" in result.reasoning
    assert mock_provider.call_count == 1

    # Second identical call should hit cache and not increment provider call count
    cached_result = await gateway.execute_structured(
        task="entity_resolution",
        prompt="Adjudicate mention",
        schema=Stage6AdjudicationOut,
        use_cache=True,
    )
    assert cached_result.decision == "match"
    assert mock_provider.call_count == 1  # Cache hit verified


# ── 3. Deterministic Cascade Tests (Stages 1 to 5) ───────────────────────────

@pytest.mark.asyncio
async def test_stage1_identifier_match_terminates_immediately(sqlite_db_session):
    """Stage 1: Authoritative identifier (LEI, CIN, etc.) match yields 1.00 confidence immediately."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="Infineon Technologies AG",
        name_norm="infineon technologies",
        country="DE",
        confidence=1.0,
    )
    sqlite_db_session.add(company)

    ident = CompanyIdentifier(
        company_id=comp_id,
        identifier_type="lei",
        identifier_value="529900UPN73BP33T4713",
        issuing_country="DE",
    )
    sqlite_db_session.add(ident)
    await sqlite_db_session.commit()

    cascade = EntityResolutionCascade(sqlite_db_session)
    res = await cascade.resolve(
        name="Unknown Variant Name",
        identifiers={"lei": "529900UPN73BP33T4713"},
    )

    assert res.matched is True
    assert res.stage == 1
    assert res.match_method == "identifier"
    assert res.confidence == 1.00
    assert res.company_id == comp_id


@pytest.mark.asyncio
async def test_stage2_domain_match_rejects_freemail(sqlite_db_session):
    """Stage 2: Domain match yields 0.97 confidence and rejects free-mail domains."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="TSMC Taiwan",
        name_norm="tsmc taiwan",
        country="TW",
        primary_domain="tsmc.com",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.commit()

    cascade = EntityResolutionCascade(sqlite_db_session)

    # Valid company domain
    res_domain = await cascade.resolve(
        name="TSMC Fabricator",
        domain="www.tsmc.com",
    )
    assert res_domain.matched is True
    assert res_domain.stage == 2
    assert res_domain.match_method == "domain"
    assert res_domain.confidence == 0.97
    assert res_domain.company_id == comp_id

    # Free-mail domain must NOT match
    res_freemail = await cascade.resolve(
        name="Some Other Supplier",
        domain="gmail.com",
        auto_review=False,
    )
    assert res_freemail.matched is False


@pytest.mark.asyncio
async def test_stage3_exact_normalized_name_and_country(sqlite_db_session):
    """Stage 3: Exact normalized name + country yields 0.95 confidence."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="Texas Instruments Incorporated",
        name_norm="texas instruments",
        country="US",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.commit()

    cascade = EntityResolutionCascade(sqlite_db_session)
    res = await cascade.resolve(
        name="Texas Instruments Inc.",
        country="US",
    )
    assert res.matched is True
    assert res.stage == 3
    assert res.match_method == "exact_name_country"
    assert res.confidence == 0.95
    assert res.company_id == comp_id


@pytest.mark.asyncio
async def test_stage4_exact_normalized_name_unique_hit(sqlite_db_session):
    """Stage 4: Unique exact normalized name without country yields 0.85 confidence."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="Foxconn Technology Co., Ltd.",
        name_norm="foxconn technology",
        country="TW",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.commit()

    cascade = EntityResolutionCascade(sqlite_db_session)
    res = await cascade.resolve(
        name="Foxconn Technology Ltd",
        country=None,  # No country provided
    )
    assert res.matched is True
    assert res.stage == 4
    assert res.match_method == "exact_name"
    assert res.confidence == 0.85
    assert res.company_id == comp_id


@pytest.mark.asyncio
async def test_stage5_fuzzy_similarity_auto_accept(sqlite_db_session):
    """Stage 5: High fuzzy similarity (>= 0.90) auto-accepts without invoking AI."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="Schneider Electric Industries SAS",
        name_norm="schneider electric industries",
        country="FR",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.commit()

    cascade = EntityResolutionCascade(sqlite_db_session)
    # Slight typo / word order: "Schneider Electric Industry"
    res = await cascade.resolve(
        name="Schneider Electric Industry",
        country="FR",
    )
    assert res.matched is True
    assert res.stage == 5
    assert res.match_method == "fuzzy"
    assert res.confidence >= 0.90
    assert res.company_id == comp_id


# ── 4. Stage 6 AI Adjudication & Guardrails ──────────────────────────────────

@pytest.mark.asyncio
async def test_stage6_ai_adjudication_accepts_when_high_confidence(sqlite_db_session):
    """Stage 6: When in ambiguous band (0.60-0.90), AI adjudicates and matches if confidence >= 0.85."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="STMicroelectronics N.V.",
        name_norm="stmicroelectronics",
        country="CH",
        primary_domain="st.com",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.commit()

    mock_provider = MockProvider()
    mock_provider.add_response(
        Stage6AdjudicationOut(
            decision="match",
            company_id=str(comp_id),
            confidence=0.88,
            reasoning="STMicro Ireland Operations is an active operating subsidiary of STMicroelectronics N.V.",
            evidence_fields=["primary_domain", "corporate_group"],
        )
    )

    gateway = LLMGateway(db=sqlite_db_session, provider=mock_provider)
    cascade = EntityResolutionCascade(sqlite_db_session, gateway=gateway)

    res = await cascade.resolve(
        name="STMicro Ireland Operations",
        country="IE",
        domain=None,
    )

    assert res.matched is True
    assert res.stage == 6
    assert res.match_method == "ai"
    assert res.confidence == 0.88
    assert res.company_id == comp_id
    assert "operating subsidiary" in (res.reasoning or "")


@pytest.mark.asyncio
async def test_stage6_ai_guardrail_rejects_invented_company_id(sqlite_db_session):
    """Guardrail test: Model-hallucinated company_id NOT in candidate list must be rejected."""
    comp_id = uuid.uuid4()
    company = Company(
        id=comp_id,
        legal_name="Qualcomm Technologies",
        name_norm="qualcomm technologies",
        country="US",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.commit()

    invented_id = str(uuid.uuid4())
    mock_provider = MockProvider()
    mock_provider.add_response(
        Stage6AdjudicationOut(
            decision="match",
            company_id=invented_id,  # Invented ID not in candidate list!
            confidence=0.95,
            reasoning="Hallucinated candidate match",
            evidence_fields=[],
        )
    )

    gateway = LLMGateway(db=sqlite_db_session, provider=mock_provider)
    cascade = EntityResolutionCascade(sqlite_db_session, gateway=gateway)

    # Ambiguous query
    res = await cascade.resolve(
        name="Q-Comm Wireless Div",
        country="US",
        auto_review=True,
    )

    # Must NOT accept invented ID; must escalate to Stage 7 Review Queue
    assert res.matched is False
    assert res.stage == 7
    assert res.review_id is not None


# ── 5. Stage 7 Review Queue & Review Resolution Workflow ─────────────────────

@pytest.mark.asyncio
async def test_stage7_review_queue_and_manual_resolve(sqlite_db_session):
    """Stage 7: Ambiguous or unmatched items insert into review queue and can be resolved."""
    cascade = EntityResolutionCascade(sqlite_db_session)
    res = await cascade.resolve(
        name="Unidentifiable Quantum Components Ltd",
        country="UK",
        auto_review=True,
    )

    assert res.matched is False
    assert res.stage == 7
    assert res.review_id is not None

    # Verify review record in DB
    review_stmt = select(EntityResolutionReview).where(EntityResolutionReview.id == res.review_id)
    review_res = await sqlite_db_session.execute(review_stmt)
    review = review_res.scalar_one()

    assert review.status == "pending"
    assert review.raw_name == "Unidentifiable Quantum Components Ltd"

    # Resolve manually by creating new entity
    company = Company(
        legal_name="Quantum Components UK Ltd",
        name_norm="quantum components uk",
        country="GB",
    )
    sqlite_db_session.add(company)
    await sqlite_db_session.flush()

    review.status = "resolved"
    review.resolved_company_id = company.id
    review.resolved_by = "test_analyst"
    review.resolved_at = datetime.now(timezone.utc)
    await sqlite_db_session.commit()

    assert review.status == "resolved"
    assert review.resolved_company_id == company.id


# ── 6. GLEIF Enrichment & Hierarchy Seeding ──────────────────────────────────

@pytest.mark.asyncio
async def test_gleif_enrichment_seeds_owned_by_edge(sqlite_db_session):
    """GLEIF enrichment job must seed Level 2 corporate hierarchy into supplier_relationships."""
    org_id = uuid.uuid4()
    sub_id = uuid.uuid4()

    subsidiary = Company(
        id=sub_id,
        legal_name="Applied Materials Ireland Ltd",
        name_norm="applied materials ireland",
        country="IE",
    )
    sqlite_db_session.add(subsidiary)

    # Add existing LEI for subsidiary
    sub_lei = CompanyIdentifier(
        company_id=sub_id,
        identifier_type="lei",
        identifier_value="5493006MHB84DD0ZWV18",
    )
    sqlite_db_session.add(sub_lei)
    await sqlite_db_session.commit()

    service = GleifEnrichmentService(sqlite_db_session)

    # Mock GLEIF API responses
    fake_sub_record = {
        "attributes": {
            "lei": "5493006MHB84DD0ZWV18",
            "entity": {"legalName": {"name": "Applied Materials Ireland Ltd"}, "jurisdiction": "IE"},
        },
        "relationships": {
            "direct-parent": {"data": {"id": "254900X7V4O7J1D8Y420"}},
            "ultimate-parent": {"data": {"id": "254900X7V4O7J1D8Y420"}},
        },
    }
    fake_parent_record = {
        "attributes": {
            "lei": "254900X7V4O7J1D8Y420",
            "entity": {"legalName": {"name": "Applied Materials Inc."}, "jurisdiction": "US"},
        }
    }

    with patch.object(service, "fetch_lei_record", side_effect=lambda lei: fake_sub_record if lei == "5493006MHB84DD0ZWV18" else fake_parent_record):
        res = await service.enrich_company(sub_id, org_id=org_id)

    assert res["status"] == "enriched"
    assert len(res["parents_seeded"]) >= 1
    seeded = res["parents_seeded"][0]
    assert seeded["org_id"] == str(org_id)
    assert seeded["parent_lei"] == "254900X7V4O7J1D8Y420"

    # Verify owned_by edge in supplier_relationships
    edge_stmt = select(SupplierRelationship).where(
        SupplierRelationship.org_id == org_id,
        SupplierRelationship.from_company_id == sub_id,
        SupplierRelationship.relationship_type == "owned_by",
    )
    edge_res = await sqlite_db_session.execute(edge_stmt)
    edge = edge_res.scalar_one_or_none()

    assert edge is not None
    assert edge.source == "gleif"
    assert edge.confidence == 1.0


# ── 7. 150-Pair Eval Dataset & Acceptance Criteria ───────────────────────────

@pytest.mark.asyncio
async def test_150_pair_eval_dataset_metrics(sqlite_db_session):
    """
    Evaluates 150 company name pairs (including hard negatives).
    Verifies:
      1. Hard negatives MUST NOT merge (0 false positive merges)
      2. Precision >= 95%
      3. Recall >= 85%
      4. Stage distribution: >= 80% resolved before Stage 6
    """
    # Populate ground truth companies in database
    ground_truth_companies = [
        {"name": "Apple Inc.", "norm": "apple", "country": "US", "domain": "apple.com", "lei": "HWUPKR0MPOU8FGXBT394"},
        {"name": "Apple Corps Ltd", "norm": "apple corps", "country": "GB", "domain": "applecorps.com", "lei": "213800K1J3L99Z567890"},
        {"name": "Delta Air Lines, Inc.", "norm": "delta air lines", "country": "US", "domain": "delta.com", "lei": "549300T8X67I87G00645"},
        {"name": "Delta Electronics Inc", "norm": "delta electronics", "country": "TW", "domain": "deltaww.com", "lei": "549300M45N7Q89R01234"},
        {"name": "Tata Motors Limited", "norm": "tata motors", "country": "IN", "domain": "tatamotors.com", "lei": "335800G9012345678901"},
        {"name": "Tata Steel Limited", "norm": "tata steel", "country": "IN", "domain": "tatasteel.com", "lei": "335800H1234567890123"},
        {"name": "Rolls-Royce Motor Cars Ltd", "norm": "rolls royce motor cars", "country": "GB", "domain": "rolls-roycemotorcars.com", "lei": "213800R1234567890123"},
        {"name": "Rolls-Royce SMR Ltd", "norm": "rolls royce smr", "country": "GB", "domain": "rolls-royce-smr.com", "lei": "213800S2345678901234"},
        {"name": "Continental AG", "norm": "continental", "country": "DE", "domain": "continental.com", "lei": "529900B0257321590483"},
        {"name": "Continental Airlines Inc", "norm": "continental airlines", "country": "US", "domain": "continental.com", "lei": "549300C3456789012345"},
        {"name": "BASF SE", "norm": "basf", "country": "DE", "domain": "basf.com", "lei": "529900O5N5L934785321"},
        {"name": "Bayer AG", "norm": "bayer", "country": "DE", "domain": "bayer.com", "lei": "52990098765432109876"},
        {"name": "Sony Group Corporation", "norm": "sony group", "country": "JP", "domain": "sony.com", "lei": "353800SONY1234567890"},
        {"name": "Sony Pictures Entertainment", "norm": "sony pictures entertainment", "country": "US", "domain": "sonypictures.com", "lei": "549300SPE12345678901"},
        {"name": "Samsung Electronics Co., Ltd.", "norm": "samsung electronics", "country": "KR", "domain": "samsung.com", "lei": "98840000000000000001"},
        {"name": "Samsung Heavy Industries Co.", "norm": "samsung heavy industries", "country": "KR", "domain": "samsungshi.com", "lei": "98840000000000000002"},
        {"name": "Nippon Semiconductor Ltd", "norm": "nippon semiconductor", "country": "JP", "domain": "nippon-semi.com", "lei": "353800NIPPO123456789"},
        {"name": "Apex Precision Machining LLC", "norm": "apex precision machining", "country": "US", "domain": "apexprecision.com", "lei": "549300APEX1234567890"},
        {"name": "Nordic Microelectronics AB", "norm": "nordic microelectronics", "country": "SE", "domain": "nordicmicro.se", "lei": "549300NORDI123456789"},
        {"name": "Shenzhen Advanced Materials Co", "norm": "shenzhen advanced materials", "country": "CN", "domain": "szadvanced.cn", "lei": "988400SZADV123456789"},
    ]

    company_by_name = {}
    for comp in ground_truth_companies:
        c = Company(
            legal_name=comp["name"],
            name_norm=comp["norm"],
            country=comp["country"],
            primary_domain=comp["domain"],
        )
        sqlite_db_session.add(c)
        await sqlite_db_session.flush()

        ident = CompanyIdentifier(
            company_id=c.id,
            identifier_type="lei",
            identifier_value=comp["lei"],
            issuing_country=comp["country"],
        )
        sqlite_db_session.add(ident)
        company_by_name[comp["name"]] = c

    await sqlite_db_session.commit()

    # Build 150 test queries:
    # - 75 True Matches (abbreviations, suffix drops, domains, identifiers, minor typos)
    # - 75 Hard Negatives (distinct legal entities with similar names that must NOT merge)
    test_queries = []

    # True Matches
    for base in ground_truth_companies:
        # Variant 1: dropped suffix
        test_queries.append({
            "mention": base["name"].replace(" Inc.", "").replace(" Ltd", "").replace(" Corporation", "").replace(" LLC", "").replace(" Co., Ltd.", ""),
            "country": base["country"],
            "domain": None,
            "identifiers": None,
            "expected_company_name": base["name"],
            "is_hard_negative": False,
        })
        # Variant 2: domain match
        test_queries.append({
            "mention": f"{base['norm']} Global",
            "country": base["country"],
            "domain": base["domain"],
            "identifiers": None,
            "expected_company_name": base["name"],
            "is_hard_negative": False,
        })
        # Variant 3: LEI match
        test_queries.append({
            "mention": f"Unrecognized Trade Name for {base['norm']}",
            "country": None,
            "domain": None,
            "identifiers": {"lei": base["lei"]},
            "expected_company_name": base["name"],
            "is_hard_negative": False,
        })

    # Fill remainder of 75 true matches
    while len([q for q in test_queries if not q["is_hard_negative"]]) < 75:
        target = ground_truth_companies[len(test_queries) % len(ground_truth_companies)]
        test_queries.append({
            "mention": f"  {target['name'].upper()}  ",
            "country": target["country"],
            "domain": target["domain"],
            "identifiers": None,
            "expected_company_name": target["name"],
            "is_hard_negative": False,
        })

    # Trim true matches to exactly 75
    true_matches = [q for q in test_queries if not q["is_hard_negative"]][:75]

    # Hard Negatives: distinct entities with similar names
    hard_negative_pairs = [
        ("Delta Electronics Inc", "Delta Air Lines, Inc.", "TW"),
        ("Apple Corps Ltd", "Apple Inc.", "GB"),
        ("Tata Steel Limited", "Tata Motors Limited", "IN"),
        ("Continental Airlines Inc", "Continental AG", "US"),
        ("Rolls-Royce SMR Ltd", "Rolls-Royce Motor Cars Ltd", "GB"),
        ("Samsung Heavy Industries Co.", "Samsung Electronics Co., Ltd.", "KR"),
        ("Sony Pictures Entertainment", "Sony Group Corporation", "US"),
        ("Bayer AG", "BASF SE", "DE"),
    ]

    hard_negatives = []
    for distinct_mention, target_comp_name, country in hard_negative_pairs:
        # A query for distinct_mention must NOT resolve to target_comp_name
        for i in range(10):  # multiply variants to reach 75
            hard_negatives.append({
                "mention": f"{distinct_mention} Division {i+1}",
                "country": country,
                "domain": None,
                "identifiers": None,
                "forbidden_merge_name": target_comp_name,
                "is_hard_negative": True,
            })

    # Exactly 75 hard negatives
    hard_negatives = hard_negatives[:75]
    all_150_eval_pairs = true_matches + hard_negatives
    assert len(all_150_eval_pairs) == 150

    # Use MockProvider for any ambiguous queries that reach Stage 6
    mock_provider = MockProvider()
    gateway = LLMGateway(db=sqlite_db_session, provider=mock_provider)
    cascade = EntityResolutionCascade(sqlite_db_session, gateway=gateway)

    true_positives = 0
    false_positives = 0
    false_negatives = 0
    resolved_before_stage_6 = 0
    hard_negative_false_merges = 0

    for query in all_150_eval_pairs:
        res = await cascade.resolve(
            name=query["mention"],
            country=query.get("country"),
            domain=query.get("domain"),
            identifiers=query.get("identifiers"),
            auto_review=False,
        )

        if query["is_hard_negative"]:
            forbidden_name = query["forbidden_merge_name"]
            forbidden_comp = company_by_name[forbidden_name]
            if res.matched and res.company_id == forbidden_comp.id:
                hard_negative_false_merges += 1
                false_positives += 1
        else:
            expected_name = query["expected_company_name"]
            expected_comp = company_by_name[expected_name]
            if res.matched:
                if res.company_id == expected_comp.id:
                    true_positives += 1
                    if res.stage < 6:
                        resolved_before_stage_6 += 1
                else:
                    false_positives += 1
            else:
                false_negatives += 1

    # Precision & Recall calculation
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) else 1.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) else 0.0
    pre_stage6_ratio = resolved_before_stage_6 / len(true_matches)

    # Acceptance Criteria Assertions:
    # 1. Hard negatives MUST NOT merge
    assert hard_negative_false_merges == 0, f"Hard negatives falsely merged: {hard_negative_false_merges}"

    # 2. Precision >= 95%
    assert precision >= 0.95, f"Precision was {precision:.2%}, expected >= 95%"

    # 3. Recall >= 85%
    assert recall >= 0.85, f"Recall was {recall:.2%}, expected >= 85%"

    # 4. >= 80% resolved before Stage 6
    assert pre_stage6_ratio >= 0.80, f"Pre-Stage 6 resolution ratio was {pre_stage6_ratio:.2%}, expected >= 80%"
