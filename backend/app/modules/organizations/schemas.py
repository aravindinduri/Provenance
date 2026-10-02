"""
app/modules/organizations/schemas.py — Pydantic request/response schemas.

These are the shapes the API exposes.  They are deliberately separate from the
SQLAlchemy models so the DB schema and the API contract can evolve independently.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared / nested
# ---------------------------------------------------------------------------

class MemberOut(BaseModel):
    """A single organization member as returned by the API."""

    id: uuid.UUID
    user_id: str
    role: str
    persona: str | None
    assigned_categories: list[str]
    invited_at: datetime | None
    joined_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class OrganizationOut(BaseModel):
    """Organization record returned to clients."""

    id: uuid.UUID
    clerk_org_id: str
    name: str
    slug: str
    company_id: uuid.UUID | None
    industry: str | None
    country: str | None
    subscription_tier: str
    monthly_token_budget: int
    onboarding_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    """Fields a caller may PATCH on an organization."""

    name: str | None = Field(None, min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    country: str | None = Field(None, min_length=2, max_length=2)
    company_id: uuid.UUID | None = None
    onboarding_completed: bool | None = None
    settings: dict | None = None

    @field_validator("country")
    @classmethod
    def _upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class OrganizationCreate(BaseModel):
    """
    Payload used internally when the Clerk webhook creates a new org.
    Not exposed as a user-facing endpoint — org creation is handled by Clerk.
    """

    clerk_org_id: str
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    industry: str | None = None
    country: str | None = None


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

class MemberInvite(BaseModel):
    """Invite a user to an organization."""

    user_id: str = Field(description="Clerk user ID of the invitee")
    role: str = Field(
        default="org_user",
        description="One of: org_admin, analyst, org_user, read_only",
    )
    persona: str | None = Field(
        None,
        description="UX persona hint: risk_manager, category_manager, or other",
    )

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        allowed = {"org_admin", "analyst", "org_user", "read_only"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class MemberUpdate(BaseModel):
    """Update role or persona for an existing member."""

    role: str | None = None
    persona: str | None = None
    assigned_categories: list[str] | None = None

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"org_admin", "analyst", "org_user", "read_only"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


# ---------------------------------------------------------------------------
# /auth/me response
# ---------------------------------------------------------------------------

class MeOut(BaseModel):
    """What GET /auth/me returns — combines the JWT principal with org context."""

    user_id: str
    email: str | None
    org_id: str | None
    clerk_org_id: str | None
    role: str
    persona: str | None
    assigned_categories: list[str]
    organization: OrganizationOut | None


# ---------------------------------------------------------------------------
# Paginated list wrappers
# ---------------------------------------------------------------------------

class PaginatedMembers(BaseModel):
    data: list[MemberOut]
    total: int
