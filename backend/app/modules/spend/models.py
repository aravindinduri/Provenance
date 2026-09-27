"""
Spend module models.

Tables: uploaded_documents, contracts, purchase_orders,
        spend_records, spend_leakage_findings

All are tenant-scoped and RLS-protected.

Documents are never partially inserted into spend tables — parse_confidence
below threshold → parse_status='needs_review' and nothing flows downstream.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class UploadedDocument(AuditMixin, SoftDeleteMixin, Base):
    """
    An uploaded file (invoice PDF, PO, contract, spend CSV/XLSX).
    Parse status tracks the async pipeline. Raw file stored in S3.
    UNIQUE (org_id, content_hash) prevents duplicate uploads.
    RLS ENABLED.
    """

    __tablename__ = "uploaded_documents"
    __table_args__ = (
        UniqueConstraint("org_id", "content_hash", name="uq_uploaded_doc"),
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
    doc_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # invoice|purchase_order|contract|spend_export
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", index=True
    )  # pending|parsed|needs_review|failed
    parse_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    parsed_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parse_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    uploaded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    virus_scan_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # pending|clean|infected

    def __repr__(self) -> str:
        return f"<UploadedDocument id={self.id} status={self.parse_status!r}>"


class Contract(AuditMixin, SoftDeleteMixin, Base):
    """
    A parsed and normalized contract record.
    `agreed_unit_prices` and `payment_terms` are JSONB so varied contract
    structures don't require a rigid schema.
    RLS ENABLED.
    """

    __tablename__ = "contracts"

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
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contract_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_terms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    agreed_unit_prices: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payment_terms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_documents.id", ondelete="SET NULL"),
        nullable=True,
    )


class PurchaseOrder(AuditMixin, SoftDeleteMixin, Base):
    """
    A parsed PO record. UNIQUE (org_id, po_number) prevents duplicates.
    RLS ENABLED.
    """

    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("org_id", "po_number", name="uq_purchase_order"),
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
    po_number: Mapped[str] = mapped_column(Text, nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    line_items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_documents.id", ondelete="SET NULL"),
        nullable=True,
    )


class SpendRecord(AuditMixin, SoftDeleteMixin, Base):
    """
    A normalized line-item spend record. UNIQUE (org_id, company_id, invoice_number).
    RLS ENABLED.
    """

    __tablename__ = "spend_records"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "company_id", "invoice_number", name="uq_spend_record"
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
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    po_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    invoice_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    spend_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uploaded_documents.id", ondelete="SET NULL"),
        nullable=True,
    )


class SpendLeakageFinding(AuditMixin, Base):
    """
    A deterministic leakage finding (maverick spend, duplicate payment,
    price variance, missed discount).

    `regulatory_overlap` = True is THE differentiator: a leakage finding that
    coincides with a live risk assessment for the same supplier. Surfaced
    prominently in both persona dashboards.

    RLS ENABLED.
    """

    __tablename__ = "spend_leakage_findings"

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
    finding_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # maverick_spend|duplicate_payment|price_variance|missed_discount
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_usd: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # The differentiator — coincides with a live risk for the same supplier
    regulatory_overlap: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), index=True
    )
    risk_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Evidence must always be present — same discipline as alert_evidence
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="open", index=True
    )  # open|reviewed|dismissed|resolved
