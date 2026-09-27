"""
Risk module models.

Tables: risk_model_versions, risk_assessments

DETERMINISTIC — no LLM calls occur anywhere in this module.
The import-linter contract (pyproject.toml) enforces this at CI time:
    app.modules.risk cannot import agents.*

risk_assessments is tenant-scoped and RLS-protected.
UNIQUE (org_id, event_id, company_id) makes recomputation idempotent.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base


class RiskModelVersion(AuditMixin, Base):
    """
    Versioned risk scoring weights and severity-band thresholds.
    Every risk_assessment records which version produced it so changing
    weights never silently rewrites history — arch §I.3.
    Seeded with 'v1' defaults by database/seeds/risk_model.sql.
    """

    __tablename__ = "risk_model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    version: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )  # 'v1', 'v2', …
    weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<RiskModelVersion version={self.version!r} active={self.is_active}>"


class RiskAssessment(AuditMixin, Base):
    """
    Computed impact score for one (org, event, company) triple.

    Scores are reproducible: identical inputs + same model_version = identical score.
    `factors` JSONB contains the full arithmetic breakdown (every factor value and
    its inputs) so the score can be reconstructed from the stored data alone.
    `graph_path` is the literal edge chain that connects the event's entity to this
    tenant's graph.

    UNIQUE (org_id, event_id, company_id) — re-running the pipeline updates, not duplicates.
    RLS ENABLED — tenant-isolated.
    """

    __tablename__ = "risk_assessments"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "event_id", "company_id", name="uq_risk_assessment"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    impact_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    severity_band: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # CRITICAL|HIGH|MEDIUM|LOW|BELOW_THRESHOLD
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)

    # Full factor-by-factor arithmetic breakdown — every field in §I.3
    factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Serialized graph path: list of edge dicts with type/confidence/source
    graph_path: Mapped[dict] = mapped_column(JSONB, nullable=False)

    path_depth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    path_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # Which factor inputs were missing at computation time
    completeness: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    def __repr__(self) -> str:
        return (
            f"<RiskAssessment id={self.id} score={self.impact_score} "
            f"band={self.severity_band!r}>"
        )
