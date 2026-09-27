"""
Companies module models.

Tables: companies, company_identifiers, company_aliases, entity_resolution_reviews

`companies` is the GLOBAL, cross-tenant canonical entity registry.
`supplier_relationships` (in graph/models.py) is the tenant-scoped edge that
encodes who-buys-from-whom. This separation is the central privacy invariant —
see arch §G.3 and §12.3.

DO NOT add org_id to this table. DO NOT put RLS on this table.
These are public reference data; the comments exist so nobody "fixes" it.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class Company(AuditMixin, SoftDeleteMixin, Base):
    """
    Canonical global company record.
    Shared across all tenants — one row per legal entity, enriched from GLEIF
    and other authoritative sources.

    NOT tenant-scoped. NOT RLS-protected. This is public reference data.
    See arch §G.3: two tenants buying from the same company share one row;
    their `supplier_relationships` rows are fully isolated.
    """

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Normalized name for trigram similarity search (pg_trgm).
    # Populated by the application before insert: lowercase + strip legal suffixes + NFKC.
    name_norm: Mapped[str] = mapped_column(Text, nullable=False)

    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    primary_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    industry_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    registered_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hq_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Source that created/last enriched this record
    data_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # gleif|ogd_india|user|inferred
    enrichment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending"
    )
    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Overall data-quality confidence (0–1)
    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, server_default=text("1.0")
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    # Relationships
    identifiers: Mapped[list["CompanyIdentifier"]] = relationship(
        "CompanyIdentifier", back_populates="company", passive_deletes=True
    )
    aliases: Mapped[list["CompanyAlias"]] = relationship(
        "CompanyAlias", back_populates="company", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} legal_name={self.legal_name!r}>"


# GIN trigram index for fuzzy name search — created explicitly in the migration
# so we can specify gin_trgm_ops.
Index("ix_companies_name_norm_trgm", Company.name_norm, postgresql_using="gin",
      postgresql_ops={"name_norm": "gin_trgm_ops"})


class CompanyIdentifier(AuditMixin, Base):
    """
    Authoritative identifiers for a company (LEI, CIN, DUNS, VAT, etc.).
    The UNIQUE constraint on (identifier_type, identifier_value) is the primary
    anchor for Stage-1 entity resolution — the fastest and most certain match.
    """

    __tablename__ = "company_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "identifier_type", "identifier_value", name="uq_company_identifier"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identifier_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # lei|cin|duns|vat|tax_id|registration_number|ticker
    identifier_value: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company: Mapped["Company"] = relationship("Company", back_populates="identifiers")

    def __repr__(self) -> str:
        return f"<CompanyIdentifier {self.identifier_type}={self.identifier_value!r}>"


class CompanyAlias(AuditMixin, Base):
    """
    Known alternate names for a company (trade names, former names, abbreviations).
    Used by ER Stages 3–5.
    """

    __tablename__ = "company_aliases"
    __table_args__ = (
        UniqueConstraint("company_id", "alias_norm", name="uq_company_alias_norm"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_norm: Mapped[str] = mapped_column(Text, nullable=False)
    alias_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="aliases")


class EntityResolutionReview(AuditMixin, Base):
    """
    Human review queue row. Created when ER cascade reaches Stage 7 (ambiguous).
    `org_id` is NULL for global/system-initiated resolutions.
    Nothing else in the pipeline is blocked while this row is pending.
    """

    __tablename__ = "entity_resolution_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Top-10 candidate companies with scores from deterministic cascade
    candidates: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    suggested_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    ai_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending", index=True
    )  # pending|resolved|rejected|new_entity

    resolved_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<EntityResolutionReview id={self.id} status={self.status!r} name={self.raw_name!r}>"
