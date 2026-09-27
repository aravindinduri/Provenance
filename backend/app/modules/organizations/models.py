"""
Organizations module models.

Tables: organizations, organization_members
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class Organization(AuditMixin, SoftDeleteMixin, Base):
    """
    A tenant in the system. One row per customer account.

    `company_id` links the tenant to its own canonical Company entry in the
    global registry — so the tenant itself can be a node in its own graph.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # Clerk's organization ID — used to verify JWTs
    clerk_org_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # FK to companies(id) — nullable until onboarding completes
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="free"
    )

    # Arbitrary org-level settings (notification preferences, feature flags, etc.)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # Per-tenant monthly LLM token budget (enforced by LLMGateway)
    monthly_token_budget: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("5000000")
    )

    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember", back_populates="organization", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"


class OrganizationMember(AuditMixin, SoftDeleteMixin, Base):
    """
    Membership record linking a Clerk user_id to an organization with a role.

    `persona` is a UX hint (risk_manager / category_manager) stored separately
    from the RBAC role so persona never affects permissions — see arch §12.2.
    """

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_member"),
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
    # Clerk user ID (sub claim from JWT)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="org_user",
    )
    persona: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Category Manager scoping — list of category strings they can see by default
    assigned_categories: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )

    invited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="members"
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember org={self.org_id} user={self.user_id} role={self.role!r}>"
