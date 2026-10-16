"""
app/modules/rfx/models.py — Sourcing models (RFx events, supplier invitations, responses).

RLS ENABLED on all tables. rfx_number and response_number are sequential per org.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin
from app.modules.companies.models import Company
from app.modules.organizations.models import Organization
from app.modules.procurement.models import MaterialRequest
from app.modules.spend.models import UploadedDocument


class RFxEvent(AuditMixin, SoftDeleteMixin, Base):
    """
    Sourcing event (RFI, RFQ, RFP, RFT).
    States:
      draft → published → q_and_a → evaluation → negotiation → awarded | cancelled | closed
    RLS ENABLED.
    """

    __tablename__ = "rfx_events"
    __table_args__ = (
        UniqueConstraint("org_id", "rfx_number", name="uq_rfx_number_per_org"),
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
    rfx_number: Mapped[str] = mapped_column(Text, nullable=False)
    rfx_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="rfq")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", index=True)
    material_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("material_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_criteria: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    awarded_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    material_request = relationship("MaterialRequest", lazy="selectin")
    awarded_supplier = relationship("Company", foreign_keys=[awarded_supplier_id], lazy="joined")
    invitations: Mapped[list["RFxInvitation"]] = relationship(
        "RFxInvitation",
        back_populates="rfx_event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    responses: Mapped[list["RFxResponse"]] = relationship(
        "RFxResponse",
        back_populates="rfx_event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<RFxEvent {self.rfx_number!r} type={self.rfx_type!r} status={self.status!r}>"


class RFxInvitation(AuditMixin, SoftDeleteMixin, Base):
    """
    Invitation of a specific supplier (Company) to an RFx event.
    Statuses: invited, viewed, responded, declined, shortlisted, awarded, rejected
    RLS ENABLED.
    """

    __tablename__ = "rfx_invitations"
    __table_args__ = (
        UniqueConstraint("rfx_event_id", "supplier_id", name="uq_rfx_event_supplier_invitation"),
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
    rfx_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfx_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="invited")
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rfx_event: Mapped["RFxEvent"] = relationship("RFxEvent", back_populates="invitations")
    supplier = relationship("Company", foreign_keys=[supplier_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<RFxInvitation rfx={self.rfx_event_id} supplier={self.supplier_id} status={self.status!r}>"


class RFxResponse(AuditMixin, SoftDeleteMixin, Base):
    """
    Supplier quotation / proposal response to an RFx event.
    Line items: [{item: str, qty: float, unit_price: float, lead_time_days: int}]
    Evaluation scores: [{criterion: str, score: float, notes: str}]
    RLS ENABLED.
    """

    __tablename__ = "rfx_responses"
    __table_args__ = (
        UniqueConstraint("org_id", "response_number", name="uq_rfx_response_number_per_org"),
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
    rfx_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfx_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_number: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    evaluation_scores: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'::jsonb")
    )
    validity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[list[Any] | None] = mapped_column(
        JSONB, nullable=True, server_default=text("'[]'::jsonb")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    is_best_offer: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    rfx_event: Mapped["RFxEvent"] = relationship("RFxEvent", back_populates="responses")
    supplier = relationship("Company", foreign_keys=[supplier_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<RFxResponse {self.response_number!r} supplier={self.supplier_id} amount={self.total_amount}>"
