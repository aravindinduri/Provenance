"""
Admin module models.

Tables: audit_logs

audit_logs is APPEND-ONLY at the database level:
    REVOKE UPDATE, DELETE ON audit_logs FROM app_role;
This is applied in the migration — not enforced by SQLAlchemy (which doesn't
support revoke), but tested in tests/security/test_tenant_isolation.py.

Monthly range partitioning is set up in the migration.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """
    Append-only record of every state-changing action and every agent step.

    Partitioned by created_at (monthly) — partition creation is handled by the
    migration and a weekly maintenance job.

    NOT tenant-scoped at the RLS level (platform_admin needs cross-tenant access).
    org_id is stored as a plain column for filtering.
    """

    __tablename__ = "audit_logs"

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
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="user"
    )  # user|system|agent

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Before/after state for mutations — kept as JSONB for flexibility
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"user={self.user_id!r}>"
        )
