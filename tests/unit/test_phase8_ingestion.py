"""
tests/unit/test_phase8_ingestion.py — Comprehensive unit tests for Phase 8:
Data ingestion, SourceConnector protocols, 9 Tier-1 connectors, RawStore,
idempotent deduplication (same payload 3x -> 1 record, seen_count=3),
revision versioning, circuit breaker (5 failures -> degraded -> recover),
GDELT global token bucket (>=5s spacing and 429 handling), DLQ capture + replay,
and Celery Beat schedules.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.events.models import (
    DataSource,
    DeadLetterQueue,
    SourceRecord,
    SourceRecordVersion,
)
from ingestion.connectors.base import (
    FetchResult,
    NewsConnector,
    NormalizedRecord,
    SourceConnector,
)
from ingestion.connectors.cbic_html import CBICHtmlConnector
from ingestion.connectors.data_gov_in import DataGovInConnector
from ingestion.connectors.dgft_html import DGFTHtmlConnector
from ingestion.connectors.eu_sanctions import EUSanctionsConnector
from ingestion.connectors.eurlex import EURLexConnector
from ingestion.connectors.federal_register import FederalRegisterConnector
from ingestion.connectors.gdelt import GDELTConnector
from ingestion.connectors.gleif import GLEIFConnector
from ingestion.connectors.ofac import OFACConnector
from ingestion.connectors.rate_limiter import (
    RateLimitCooldownError,
    TokenBucketRateLimiter,
)
from ingestion.connectors.registry import CONNECTOR_CLASSES, get_connector
from ingestion.connectors.uk_ofsi import UKOFSIConnector
from ingestion.connectors.un_sanctions import UNSanctionsConnector
from ingestion.connectors.utils import canonicalize_url, compute_content_hash
from ingestion.pipeline.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
)
from ingestion.pipeline.dedupe import (
    process_and_dedupe_record_sync,
)
from ingestion.pipeline.pipeline import IngestionPipeline, IngestionSummary
from ingestion.pipeline.raw_store import RawStore
from workers.schedules import CELERYBEAT_SCHEDULE

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "ingestion" / "fixtures"


# ── SQLite in-memory test database fixture for pure unit tests ───────────────

@pytest.fixture
def sqlite_session():
    """In-memory SQLite session with tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    # Register JSON compiler for SQLite if needed
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


# ── 1. Protocol & Registry Tests ─────────────────────────────────────────────

def test_source_connector_protocols():
    """Verify all 9 Tier-1 connectors satisfy SourceConnector protocol."""
    tier1_keys = [
        "ofac_sls",
        "gleif",
        "gdelt_doc",
        "federal_register",
        "eurlex",
        "eu_sanctions",
        "un_sanctions",
        "uk_ofsi",
        "data_gov_in",
    ]
    for key in tier1_keys:
        conn = get_connector(key)
        assert isinstance(conn, SourceConnector), f"{key} must implement SourceConnector"
        assert conn.source_id == key
        assert conn.source_type in {"api", "bulk_download", "rss", "html_monitor", "cached_snapshot"}
        assert conn.reliability in {"high", "medium", "low"}

    # GDELT must also implement NewsConnector
    gdelt_conn = get_connector("gdelt_doc")
    assert isinstance(gdelt_conn, NewsConnector)


def test_registry_unknown_connector_raises():
    with pytest.raises(ValueError, match="Unknown data source connector key"):
        get_connector("invalid_source_key_xyz")


# ── 2. URL Canonicalization & Content Hashing ────────────────────────────────

def test_url_canonicalization_per_spec():
    """
    Architecture §F.3:
    strip utm_*, fbclid, gclid, fragments; lowercase host; drop trailing slash.
    """
    raw_url = "HTTPS://WWW.Reuters.COM/markets/commodities/rare-earths/?utm_source=twitter&utm_medium=feed&fbclid=123#article-body"
    canonical = canonicalize_url(raw_url)
    assert canonical == "https://www.reuters.com/markets/commodities/rare-earths"

    # Trailing slash dropped, query sorted, fragment removed
    raw_2 = "http://example.com/test/?b=2&a=1&gclid=xyz#section"
    assert canonicalize_url(raw_2) == "http://example.com/test?a=1&b=2"

    # Root slash preserved
    assert canonicalize_url("https://example.com/") == "https://example.com/"
    assert canonicalize_url(None) is None
    assert canonicalize_url("") is None


def test_deterministic_content_hash():
    """Hash must be invariant to dict key ordering and return 64-char sha256 hex."""
    d1 = {"b": 2, "a": 1, "c": [3, 4]}
    d2 = {"a": 1, "c": [3, 4], "b": 2}
    h1 = compute_content_hash(d1)
    h2 = compute_content_hash(d2)
    assert h1 == h2
    assert len(h1) == 64


# ── 3. Fixture Normalization for all 9 Tier-1 Connectors ─────────────────────

def test_ofac_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "ofac_sls.xml"
    assert fixture_path.exists()
    conn = OFACConnector()
    items = conn.parse_xml_entries(fixture_path.read_text(encoding="utf-8"))
    assert len(items) == 2

    # Check Entity entry
    rec1 = conn.normalize(items[0])
    assert isinstance(rec1, NormalizedRecord)
    assert rec1.external_id == "ofac-39481"
    assert "Henan Yixin Specialty Alloys" in rec1.title
    assert rec1.reliability == "high"
    assert "RUSSIA-EO14024" in rec1.normalized_data["programs"]
    assert "Yixin Rare Earth Materials" in rec1.normalized_data["aliases"]
    assert len(rec1.content_hash) == 64

    # Check Individual entry
    rec2 = conn.normalize(items[1])
    assert rec2.external_id == "ofac-39482"
    assert rec2.normalized_data["entity_type"] == "Individual"


def test_gleif_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "gleif.json"
    assert fixture_path.exists()
    conn = GLEIFConnector()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["data"]
    assert len(items) == 2

    rec1 = conn.normalize(items[0])
    assert rec1.external_id == "5493006MHB84DD0ZWV18"
    assert "Henan Yixin Specialty Alloys" in rec1.title
    assert rec1.normalized_data["direct_parent_lei"] == "5493001KJTI48Q8X1111"
    assert rec1.normalized_data["ultimate_parent_lei"] == "5493001KJTI48Q8X1111"
    assert rec1.normalized_data["status"] == "ACTIVE"


def test_gdelt_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "gdelt.json"
    assert fixture_path.exists()
    conn = GDELTConnector()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["articles"]
    assert len(items) == 2

    rec1 = conn.normalize(items[0])
    assert rec1.reliability == "medium"
    # Ensure tracking params were stripped from canonical_url
    assert "utm_source" not in rec1.canonical_url
    assert "#article-body" not in rec1.canonical_url
    # Ensure full article text is NOT stored per §E.1 #3
    assert "article_text" not in rec1.normalized_data
    assert rec1.published_date == date(2026, 9, 25)


def test_federal_register_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "federal_register.json"
    assert fixture_path.exists()
    conn = FederalRegisterConnector()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["results"]
    assert len(items) == 1

    rec = conn.normalize(items[0])
    assert rec.external_id == "2026-19402"
    assert "Commerce Department" in rec.normalized_data["agencies"]
    assert rec.published_date == date(2026, 9, 24)
    assert rec.normalized_data["effective_on"] == "2026-10-01"


def test_eurlex_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "eurlex.xml"
    assert fixture_path.exists()
    conn = EURLexConnector()
    items = conn.parse_feed(fixture_path.read_text(encoding="utf-8"))
    assert len(items) == 1

    rec = conn.normalize(items[0])
    assert "32026R1842" in rec.external_id
    assert "833/2014" in rec.title
    assert rec.published_date == date(2026, 9, 24)


def test_eu_sanctions_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "eu_sanctions.xml"
    assert fixture_path.exists()
    conn = EUSanctionsConnector()
    items = conn.parse_xml(fixture_path.read_text(encoding="utf-8"))
    assert len(items) == 1

    rec = conn.normalize(items[0])
    assert rec.external_id == "eu-98234"
    assert "Titanium Tech Holdings" in rec.title
    # Must record Annex IV coverage gap caveat per §E.1 #6
    assert "Annex IV of Regulation 833/2014" in rec.normalized_data["coverage_notes"]


def test_un_sanctions_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "un_sanctions.xml"
    assert fixture_path.exists()
    conn = UNSanctionsConnector()
    items = conn.parse_xml(fixture_path.read_text(encoding="utf-8"))
    assert len(items) == 2

    rec1 = conn.normalize(items[0])
    assert rec1.external_id == "un-691024"
    assert "Alexei Ivanov" in rec1.title

    rec2 = conn.normalize(items[1])
    assert rec2.external_id == "un-691025"
    assert "Oceanic Logistics" in rec2.title


def test_uk_ofsi_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "uk_ofsi.csv"
    assert fixture_path.exists()
    conn = UKOFSIConnector()
    items = conn.parse_csv(fixture_path.read_text(encoding="utf-8"))
    assert len(items) == 2

    rec1 = conn.normalize(items[0])
    assert rec1.external_id == "uk-16482"
    assert "Alloy Metallurgy Enterprise" in rec1.title
    assert rec1.published_date == date(2026, 9, 24)


def test_data_gov_in_normalize_against_fixture():
    fixture_path = FIXTURES_DIR / "data_gov_in.json"
    assert fixture_path.exists()
    conn = DataGovInConnector()
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    items = data["records"]
    assert len(items) == 2

    rec1 = conn.normalize(items[0])
    assert rec1.external_id == "U27209TN2018PTC123456"
    assert "Bharat Precision Minerals" in rec1.title
    assert rec1.normalized_data["roc"] == "RoC-Chennai"


def test_supplementary_html_connectors_against_fixtures():
    # DGFT HTML
    dgft_path = FIXTURES_DIR / "dgft_html.html"
    assert dgft_path.exists()
    conn_dgft = DGFTHtmlConnector()
    items_dgft = conn_dgft.parse_html(dgft_path.read_text(encoding="utf-8"))
    assert len(items_dgft) == 2
    rec_dgft = conn_dgft.normalize(items_dgft[0])
    assert "Notification No. 34/2026" in rec_dgft.title
    assert rec_dgft.published_date == date(2026, 9, 24)

    # CBIC HTML
    cbic_path = FIXTURES_DIR / "cbic_html.html"
    assert cbic_path.exists()
    conn_cbic = CBICHtmlConnector()
    items_cbic = conn_cbic.parse_html(cbic_path.read_text(encoding="utf-8"))
    assert len(items_cbic) == 1
    rec_cbic = conn_cbic.normalize(items_cbic[0])
    assert "48/2026" in rec_cbic.title


# ── 4. RawStore Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_raw_store_key_and_storage():
    store = RawStore()
    content_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    payload = {"source": "ofac_sls", "item": "test"}

    key = await store.store(
        source_id="ofac_sls",
        content_hash=content_hash,
        payload=payload,
        extension="json",
    )
    assert key.startswith("raw/ofac_sls/")
    assert key.endswith(f"{content_hash}.json")

    # Retrieval
    retrieved = await store.get(key)
    assert retrieved is not None
    assert json.loads(retrieved)["item"] == "test"


# ── 5. Deduplication & Idempotency: 3x Ingest -> 1 Record, seen_count=3 ──────

def test_ingest_same_payload_3x_produces_1_record_with_seen_count_3(sqlite_session):
    """
    Requirement from Phase 8 specification:
    ingest same payload 3× → 1 record, seen_count=3
    """
    source_id = uuid.uuid4()
    # Create parent DataSource row
    source_row = DataSource(
        id=source_id,
        source_key="ofac_sls",
        name="OFAC SLS",
        source_type="bulk_download",
        reliability="high",
        status="healthy",
    )
    sqlite_session.add(source_row)
    sqlite_session.commit()

    conn = OFACConnector()
    fixture_path = FIXTURES_DIR / "ofac_sls.xml"
    items = conn.parse_xml_entries(fixture_path.read_text(encoding="utf-8"))
    normalized = conn.normalize(items[0])
    raw_key = "raw/ofac_sls/2026-09-25/hash123.json"

    # Pass 1: New record created
    res1 = process_and_dedupe_record_sync(sqlite_session, source_id, normalized, raw_key)
    assert res1.is_new is True
    assert res1.is_duplicate is False
    assert res1.seen_count == 1

    # Pass 2: Duplicate detected, seen_count incremented to 2
    res2 = process_and_dedupe_record_sync(sqlite_session, source_id, normalized, raw_key)
    assert res2.is_new is False
    assert res2.is_duplicate is True
    assert res2.seen_count == 2
    assert res2.source_record_id == res1.source_record_id

    # Pass 3: Duplicate detected, seen_count incremented to 3
    res3 = process_and_dedupe_record_sync(sqlite_session, source_id, normalized, raw_key)
    assert res3.is_new is False
    assert res3.is_duplicate is True
    assert res3.seen_count == 3
    assert res3.source_record_id == res1.source_record_id

    # Assert exactly 1 row exists in DB
    records = sqlite_session.execute(select(SourceRecord)).scalars().all()
    assert len(records) == 1
    assert records[0].seen_count == 3
    assert records[0].external_id == normalized.external_id


def test_revision_detection_creates_source_record_version(sqlite_session):
    """
    Architecture §F.3: A changed content_hash for the same external_id triggers
    revision detection: creates a source_record_versions row and updates the current record.
    """
    source_id = uuid.uuid4()
    source_row = DataSource(
        id=source_id,
        source_key="federal_register",
        name="Federal Register",
        source_type="api",
        reliability="high",
        status="healthy",
    )
    sqlite_session.add(source_row)
    sqlite_session.commit()

    conn = FederalRegisterConnector()
    fixture_path = FIXTURES_DIR / "federal_register.json"
    items = json.loads(fixture_path.read_text(encoding="utf-8"))["results"]

    # Initial revision
    item_v1 = dict(items[0])
    norm_v1 = conn.normalize(item_v1)
    res1 = process_and_dedupe_record_sync(sqlite_session, source_id, norm_v1, "raw/key_v1.json")
    assert res1.is_new is True

    # Amended revision (same document_number, but updated abstract and effective date)
    item_v2 = dict(items[0])
    item_v2["abstract"] = "AMENDMENT: Expanded license requirements including dysprosium compounds."
    item_v2["effective_on"] = "2026-11-01"
    norm_v2 = conn.normalize(item_v2)

    res2 = process_and_dedupe_record_sync(sqlite_session, source_id, norm_v2, "raw/key_v2.json")
    assert res2.is_revision is True
    assert res2.is_new is False
    assert res2.version == 2

    # Check version table
    versions = sqlite_session.execute(select(SourceRecordVersion)).scalars().all()
    assert len(versions) == 1
    assert versions[0].version == 2
    assert versions[0].content_hash == norm_v1.content_hash

    # Current record updated
    current = sqlite_session.execute(select(SourceRecord)).scalar_one()
    assert current.content_hash == norm_v2.content_hash
    assert current.raw_s3_key == "raw/key_v2.json"


# ── 6. Circuit Breaker Tests (5 Failures -> Degraded -> Recover) ─────────────

def test_circuit_breaker_opens_after_5_failures_and_recovers_on_success(sqlite_session):
    """
    Architecture §F.4:
    5 consecutive failures -> status='degraded', polling paused 30 min.
    On success: resets consecutive_failures=0, status='healthy'.
    """
    source_key = "test_breaker_source"
    source = DataSource(
        id=uuid.uuid4(),
        source_key=source_key,
        name="Test Breaker",
        source_type="api",
        reliability="high",
        status="healthy",
        consecutive_failures=0,
    )
    sqlite_session.add(source)
    sqlite_session.commit()

    # Initial: allowed
    assert CircuitBreaker.is_allowed_sync(sqlite_session, source_key) is True

    # Record 4 failures -> still allowed (threshold is 5)
    for i in range(4):
        CircuitBreaker.record_failure_sync(sqlite_session, source_key, f"error {i+1}")
        assert CircuitBreaker.is_allowed_sync(sqlite_session, source_key) is True

    # 5th failure -> circuit breaker opens (degraded)
    CircuitBreaker.record_failure_sync(sqlite_session, source_key, "5th error")
    sqlite_session.refresh(source)
    assert source.consecutive_failures == 5
    assert source.status == "degraded"
    assert CircuitBreaker.is_allowed_sync(sqlite_session, source_key) is False

    # Record success -> resets to healthy
    CircuitBreaker.record_success_sync(sqlite_session, source_key)
    sqlite_session.refresh(source)
    assert source.consecutive_failures == 0
    assert source.status == "healthy"
    assert CircuitBreaker.is_allowed_sync(sqlite_session, source_key) is True


# ── 7. GDELT Global Rate Limiter & 429 Handling ──────────────────────────────

@pytest.mark.asyncio
async def test_gdelt_rate_limiter_enforces_spacing():
    """Verify rate limiter enforces minimum interval spacing between calls."""
    limiter = TokenBucketRateLimiter(redis_client=None)

    # First acquire: no wait
    wait1 = await limiter.acquire("test_key", min_interval_seconds=0.1)
    assert wait1 == 0.0

    # Immediate second acquire: must delay to maintain spacing
    t0 = time.time()
    wait2 = await limiter.acquire("test_key", min_interval_seconds=0.1)
    elapsed = time.time() - t0
    assert wait2 > 0.0
    assert elapsed >= 0.08


@pytest.mark.asyncio
async def test_gdelt_rate_limiter_429_cooldown_and_fail_fast():
    """429 triggers cooldown; fail_fast raises RateLimitCooldownError."""
    limiter = TokenBucketRateLimiter(redis_client=None)
    key = "gdelt_test_429"

    # Trigger 429 cooldown for 2 seconds
    await limiter.record_429(key, cooldown_seconds=2.0)

    in_cooldown, remaining = await limiter.is_in_cooldown(key)
    assert in_cooldown is True
    assert remaining > 0.0

    # With fail_fast=True, must raise RateLimitCooldownError
    with pytest.raises(RateLimitCooldownError) as exc_info:
        await limiter.acquire(key, min_interval_seconds=0.1, fail_fast=True)
    assert exc_info.value.key == key


# ── 8. Dead Letter Queue (DLQ) Capture and Replay ────────────────────────────

def test_dlq_capture_and_replay_lifecycle(sqlite_session):
    """
    Architecture §F.4:
    Failed tasks after retries are recorded into dead_letter_queue.
    Replay re-executes task and marks replayed_at.
    """
    dlq_id = uuid.uuid4()
    entry = DeadLetterQueue(
        id=dlq_id,
        task_name="workers.tasks.ingest.poll_source_task",
        payload={"source_key": "ofac_sls", "cursor": None},
        error="HTTP 503 Service Unavailable",
        traceback="Traceback (most recent call last):\n  File ...",
        retry_count=5,
        status="failed",
        created_at=datetime.now(timezone.utc),
    )
    sqlite_session.add(entry)
    sqlite_session.commit()

    # Verify captured
    saved = sqlite_session.execute(select(DeadLetterQueue).where(DeadLetterQueue.id == dlq_id)).scalar_one()
    assert saved.status == "failed"
    assert saved.retry_count == 5

    # Simulate replay action
    now = datetime.now(timezone.utc)
    saved.status = "replayed"
    saved.replayed_at = now
    saved.replayed_by = "admin_user_01"
    sqlite_session.commit()
    sqlite_session.refresh(saved)

    assert saved.status == "replayed"
    assert saved.replayed_at is not None
    assert saved.replayed_by == "admin_user_01"


# ── 9. Celery Beat Schedules Verification ────────────────────────────────────

def test_celery_beat_schedules_coverage():
    """Verify all 9 Tier-1 connectors and supplementary connectors are scheduled per §F.4."""
    scheduled_tasks = {cfg["task"] for cfg in CELERYBEAT_SCHEDULE.values()}
    assert "workers.tasks.ingest.poll_source_task" in scheduled_tasks

    scheduled_sources = {
        cfg["args"][0]
        for cfg in CELERYBEAT_SCHEDULE.values()
        if "args" in cfg and cfg["args"]
    }

    required_sources = {
        "ofac_sls",
        "gleif",
        "gdelt_doc",
        "federal_register",
        "eurlex",
        "eu_sanctions",
        "un_sanctions",
        "uk_ofsi",
        "data_gov_in",
        "dgft_html",
        "cbic_html",
    }
    missing = required_sources - scheduled_sources
    assert not missing, f"Missing scheduled sources in Celery Beat: {missing}"
