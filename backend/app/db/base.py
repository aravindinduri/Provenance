"""
SQLAlchemy declarative Base and shared column mixins.

Every ORM model in the application imports Base from here.
Convention applied to all tables:
  - id           UUID, primary key, gen_random_uuid()
  - created_at   TIMESTAMPTZ, server default NOW()
  - updated_at   TIMESTAMPTZ, maintained by a DB trigger
  - created_by   TEXT (Clerk user_id or service principal), nullable
  - updated_by   TEXT, nullable
  - deleted_at   TIMESTAMPTZ NULL  — soft-delete; partial indexes use WHERE deleted_at IS NULL
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Common declarative base for all Provenance ORM models."""

    type_annotation_map: dict[Any, Any] = {
        datetime: DateTime(timezone=True),
    }


class AuditMixin:
    """
    Adds the standard audit columns to a model.
    `updated_at` is kept current by the `set_updated_at` DB trigger
    (created in the Alembic migration — not by SQLAlchemy events, so it
    works correctly even when rows are mutated via raw SQL or Alembic scripts).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)


class SoftDeleteMixin:
    """Adds deleted_at for soft-delete. Queries must filter WHERE deleted_at IS NULL."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=False,  # covered by partial indexes per table
    )
