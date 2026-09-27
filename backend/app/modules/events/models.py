"""
Events module models.

Tables: data_sources, source_records, source_record_versions,
        dead_letter_queue, events, event_source_records, event_entities

Events are GLOBAL — the same export ban affects many tenants.
Tenant scoping happens downstream in risk_assessments and alerts.
This is a deliberate normalization choice — see arch §D.2 events.

DO NOT add org_id to events, source_records, or data_sources.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base


class DataSource(AuditMixin, Base):
    """
    Registry of external data sources (connectors).
    One row per source (ofac_sls, gdelt_doc, gleif, etc.).
    Seeded by database/seeds/data_sources.sql.
    """

    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Machine-readable key used in code, e.g. 'ofac_sls', 'gdelt_doc'
    source_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # api|bulk_download|rss|html_monitor|cached_snapshot
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    reliability: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="high"
    )  # high|medium|low

    # Licence metadata — terms_verified_at surfaces in admin UI (arch §E.x)
    license_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_verified_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    poll_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="healthy"
    )  # healthy|degraded|failed

    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    # Arbitrary connector config (API keys are stored in Secrets Manager, referenced here by name)
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    source_records: Mapped[list["SourceRecord"]] = relationship(
        "SourceRecord", back_populates="source", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<DataSource key={self.source_key!r} status={self.status!r}>"


class SourceRecord(AuditMixin, Base):
    """
    Raw ingested item from a data source, stored before normalization.
    Full payload archived to S3 (raw_s3_key); normalized fields kept in JSONB.

    Three-layer idempotency:
      1. UNIQUE (source_id, external_id)
      2. UNIQUE (source_id, content_hash)
      3. Semantic event clustering downstream (event_cluster_key)
    """

    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_source_record_ext_id"),
        UniqueConstraint("source_id", "content_hash", name="uq_source_record_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # sha256 hex
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    raw_s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[dict] = mapped_column(JSONB, nullable=False)

    source_type: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # live|cached
    reliability: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str | None] = mapped_column(String(2), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending", index=True
    )

    # Idempotency counters — updated on ON CONFLICT DO UPDATE
    seen_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    source: Mapped["DataSource"] = relationship(
        "DataSource", back_populates="source_records"
    )
    versions: Mapped[list["SourceRecordVersion"]] = relationship(
        "SourceRecordVersion", back_populates="source_record", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<SourceRecord id={self.id} status={self.processing_status!r}>"


class SourceRecordVersion(Base):
    """
    Tracks revisions of a source record when content_hash changes for the same
    external_id. The event that was originally extracted from this record
    references the specific version it used, so alerts remain explainable
    even after the source is amended.
    """

    __tablename__ = "source_record_versions"
    __table_args__ = (
        UniqueConstraint(
            "source_record_id", "version", name="uq_source_record_version"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    source_record: Mapped["SourceRecord"] = relationship(
        "SourceRecord", back_populates="versions"
    )


class DeadLetterQueue(Base):
    """
    Failed tasks after all retry attempts. Admin portal supports inspect + replay.
    Nothing is silently dropped — arch §F.4.
    """

    __tablename__ = "dead_letter_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    task_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="failed", index=True
    )  # failed|replayed|resolved
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    replayed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replayed_by: Mapped[str | None] = mapped_column(String, nullable=True)


class Event(AuditMixin, Base):
    """
    A normalized, deduplicated event extracted from one or more source records.

    GLOBAL — not tenant-scoped. The same export ban is one event regardless of
    how many tenants it affects. Tenant impact is computed in risk_assessments.

    `event_cluster_key` drives semantic deduplication across sources (arch §F.3):
    multiple articles about the same ban produce one Event with a higher
    corroboration_count, not 40 events.
    """

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_cluster_key: Mapped[str] = mapped_column(
        Text, nullable=False, index=True
    )  # hash(event_type + jurisdiction + materials + effective_date)

    event_type: Mapped[str] = mapped_column(
        String(60), nullable=False, index=True
    )
    # ISO-3166-1 alpha-2 array
    jurisdictions: Mapped[list[str]] = mapped_column(
        ARRAY(String(2)), nullable=False, server_default=text("'{}'::text[]")
    )
    affected_materials: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    affected_hs_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Our own paraphrase — never reproduced source text (arch §E.3 / §Q copyright)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    severity_signal: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # low|moderate|high|severe
    confidence: Mapped[float | None] = mapped_column(
        Integer, nullable=True
    )  # stored as integer 0-100 for DB efficiency, /100 in app layer

    # Incremented each time a new source record corroborates this event
    corroboration_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="active", index=True
    )  # active|superseded|extraction_failed
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Which model/prompt extracted this event — for audit + eval
    extracted_by_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    entities: Mapped[list["EventEntity"]] = relationship(
        "EventEntity", back_populates="event", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} type={self.event_type!r} status={self.status!r}>"


# Full-text search index on summary — GIN over tsvector
Index(
    "ix_events_summary_fts",
    text("to_tsvector('english', summary)"),
    postgresql_using="gin",
)
# GIN index on jurisdictions array
Index(
    "ix_events_jurisdictions_gin",
    Event.jurisdictions,
    postgresql_using="gin",
)


class EventSourceRecord(Base):
    """
    Many-to-many: one event, many corroborating source records.
    """

    __tablename__ = "event_source_records"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "source_record_id", name="uq_event_source_record"
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="CASCADE"),
        primary_key=True,
    )


class EventEntity(AuditMixin, Base):
    """
    A company mention extracted from an event, with resolution metadata.
    `company_id` is null when resolution reached Stage 7 (still in review).
    """

    __tablename__ = "event_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_mention: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # subject|affected|issuer

    resolution_confidence: Mapped[float | None] = mapped_column(
        Integer, nullable=True
    )  # 0-100
    resolution_method: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # identifier|domain|exact|fuzzy|ai|unresolved

    # Character offsets in the original source text — validated post-extraction
    evidence_span: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="entities")

    def __repr__(self) -> str:
        return f"<EventEntity mention={self.raw_mention!r} method={self.resolution_method!r}>"
