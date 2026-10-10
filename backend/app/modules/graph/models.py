"""
Graph module models.

Tables: supplier_relationships, locations, company_locations

`supplier_relationships` is the ONLY table encoding who-buys-from-whom.
It carries org_id on every row and is RLS-protected — the tenant-isolation
boundary described in arch §G.3 / §12.3.

Edges are temporal (valid_from / valid_to) and never hard-deleted so that
historical alerts can still explain themselves correctly.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin
from app.modules.events.models import SourceRecord  # noqa: F401


class SupplierRelationship(AuditMixin, SoftDeleteMixin, Base):
    """
    A directed edge in the tenant's supply graph.

    RLS ENABLED — every query must have app.current_org_id set in the session.
    This is enforced at: route dependency, repository guard, and DB RLS policy.

    `to_company_id` or `to_org_id` must be non-null (CHECK constraint).
    - `to_org_id` is set for the direct supplier → this tenant edge.
    - `to_company_id` is set for company → company sub-supply edges.
    """

    __tablename__ = "supplier_relationships"
    __table_args__ = (
        CheckConstraint(
            "to_company_id IS NOT NULL OR to_org_id IS NOT NULL",
            name="ck_sr_has_target",
        ),
        CheckConstraint(
            "criticality BETWEEN 1 AND 5",
            name="ck_sr_criticality_range",
        ),
        # Partial indexes created explicitly in the migration with WHERE valid_to IS NULL
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    # Tenant scope — RLS policy enforces this matches current_setting('app.current_org_id')
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    from_company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    to_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # supplies_to|sub_supplies_to|owned_by|located_in

    tier: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    criticality: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    annual_spend_usd: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    single_source: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Edge-level data quality
    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, server_default=text("1.0")
    )
    source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="user_declared"
    )  # user_declared|gleif|inferred|document
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Temporal validity — edges are never hard-deleted; valid_to IS NULL = active
    valid_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=text("CURRENT_DATE")
    )
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by: Mapped[str | None] = mapped_column(String, nullable=True)

    # inherited_from_edge_id for sub_supplies_to edges seeded by graph traversal
    inherited_from_edge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_relationships.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SupplierRelationship id={self.id} "
            f"type={self.relationship_type!r} org={self.org_id}>"
        )


# Partial indexes for active edges — defined here so Alembic autogenerate sees them.
# Created with WHERE valid_to IS NULL in the migration.
Index(
    "ix_sr_org_from_active",
    SupplierRelationship.org_id,
    SupplierRelationship.from_company_id,
    postgresql_where=text("valid_to IS NULL"),
)
Index(
    "ix_sr_org_to_active",
    SupplierRelationship.org_id,
    SupplierRelationship.to_company_id,
    postgresql_where=text("valid_to IS NULL"),
)


class Location(Base):
    """
    A geographic point: country + optional region/city + lat/lon.
    Shared reference data — not tenant-scoped.
    """

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lon: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    geohash: Mapped[str | None] = mapped_column(String(12), nullable=True)

    company_locations: Mapped[list["CompanyLocation"]] = relationship(
        "CompanyLocation", back_populates="location", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Location id={self.id} country={self.country!r} city={self.city!r}>"


class CompanyLocation(AuditMixin, Base):
    """
    Junction between a Company and a Location, with site metadata.
    Temporal (valid_from/valid_to) and confidence-tracked.
    Not tenant-scoped — a company's HQ location is public fact.
    """

    __tablename__ = "company_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # hq|plant|warehouse|office
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, server_default=text("1.0")
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    location: Mapped["Location"] = relationship(
        "Location", back_populates="company_locations"
    )
