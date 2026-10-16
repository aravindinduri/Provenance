"""
app/modules/procurement/models.py — Purchase requisition (material request) models.

RLS ENABLED on both tables. mr_number is sequential per org.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class MaterialRequest(AuditMixin, SoftDeleteMixin, Base):
    """
    Purchase requisition. States:
      draft → pending_approval → approved → ordered → partially_ordered → cancelled
    RLS ENABLED.
    """

    __tablename__ = "material_requests"
    __table_args__ = (
        UniqueConstraint("org_id", "mr_number", name="uq_mr_number_per_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mr_number: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="draft")
    requested_by: Mapped[str | None] = mapped_column(String, nullable=True)
    required_by_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True, server_default="medium")
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_estimated_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    line_items: Mapped[list["MaterialRequestItem"]] = relationship(
        "MaterialRequestItem",
        back_populates="material_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MaterialRequest {self.mr_number!r} status={self.status!r}>"


class MaterialRequestItem(AuditMixin, SoftDeleteMixin, Base):
    """Line item on a material request. item_id is nullable (free-text allowed)."""

    __tablename__ = "material_request_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("material_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_of_measure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_unit_price: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    preferred_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    material_request: Mapped["MaterialRequest"] = relationship(
        "MaterialRequest", back_populates="line_items"
    )
