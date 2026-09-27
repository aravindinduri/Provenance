"""
Alerts module models.

Tables: alerts, alert_evidence, alert_actions

Both are tenant-scoped and RLS-protected.

The DB-level constraint `alert_must_have_evidence` (deferred trigger in the
migration) enforces engineering rule 9: an alert cannot exist without at least
one alert_evidence row. This is enforced by the database, not by convention.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class Alert(AuditMixin, SoftDeleteMixin, Base):
    """
    A supply-chain risk alert surfaced to one or more user personas.

    `target_personas` determines which dashboard views this alert appears in.
    It is NOT a permission check — the role on OrganizationMember controls access;
    persona is a UX routing hint only.

    RLS ENABLED — tenant-isolated.
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    severity_band: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    impact_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)

    # True when confidence is below threshold — rendered as "needs human judgment"
    needs_human_judgment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # UX routing — risk_manager|category_manager or both
    target_personas: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{risk_manager,category_manager}'::text[]"),
    )
    # Category for category-manager scoping
    category: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="new", index=True
    )  # new|acknowledged|investigating|escalated|dismissed|resolved
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)

    # Which model/prompt version generated the explanation
    explanation_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    explanation_prompt_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    first_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    evidence: Mapped[list["AlertEvidence"]] = relationship(
        "AlertEvidence", back_populates="alert", passive_deletes=True
    )
    actions: Mapped[list["AlertAction"]] = relationship(
        "AlertAction", back_populates="alert", passive_deletes=True
    )

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} severity={self.severity_band!r} "
            f"status={self.status!r}>"
        )


# Primary query index: org → status + severity + recency
Index(
    "ix_alerts_org_status_severity",
    Alert.org_id,
    Alert.status,
    Alert.severity_band,
    Alert.created_at,
    postgresql_ops={"created_at": "DESC NULLS LAST"},
)


class AlertEvidence(Base):
    """
    One piece of evidence supporting an alert.

    evidence_type determines which FK is populated:
      source_record → source_record_id
      graph_path    → payload (serialized path)
      spend_record  → payload
      document_chunk → chunk_id
      score_factor  → payload (factor breakdown)

    `display_order` controls the order they render in the UI.

    The `alert_must_have_evidence` trigger in the migration guarantees
    every alert has at least one row here before it can be committed.
    """

    __tablename__ = "alert_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # source_record|graph_path|spend_record|document_chunk|score_factor

    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # live|cached
    retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Paraphrased excerpt — never raw source text (copyright/injection rule)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    alert: Mapped["Alert"] = relationship("Alert", back_populates="evidence")

    def __repr__(self) -> str:
        return f"<AlertEvidence id={self.id} type={self.evidence_type!r}>"


class AlertAction(Base):
    """
    Immutable audit trail of user actions on an alert
    (Acknowledge, Escalate, Dismiss, etc.).
    """

    __tablename__ = "alert_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    alert: Mapped["Alert"] = relationship("Alert", back_populates="actions")
