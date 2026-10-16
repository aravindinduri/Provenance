"""
app/modules/goods_receipts/models.py — Goods Receipt Note (GRN) models.

RLS ENABLED. grn_number is sequential per org.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, SoftDeleteMixin


class GoodsReceipt(AuditMixin, SoftDeleteMixin, Base):
    """
    Goods Receipt Note (GRN) recorded against a Purchase Order.
    Statuses:
      draft → confirmed | partial
    RLS ENABLED.
    """

    __tablename__ = "goods_receipts"
    __table_args__ = (
        UniqueConstraint("org_id", "grn_number", name="uq_goods_receipt_grn_number"),
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
    grn_number: Mapped[str] = mapped_column(Text, nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_by: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft", index=True
    )
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    delivery_note_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    carrier: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase_order = relationship("PurchaseOrder", back_populates="receipts", lazy="joined")

    def __repr__(self) -> str:
        return f"<GoodsReceipt {self.grn_number!r} po={self.purchase_order_id} status={self.status!r}>"
