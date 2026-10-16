"""Phase 4 — Invoices & 3-Way Matching

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16

Covers Phase 4 of the procurement architecture:
  - Extends spend_records table with full invoice and matching fields:
      invoice_date, due_date, payment_status, match_status, match_exceptions,
      goods_receipt_id, approved_by, approved_at, paid_at, line_items, notes.
  - Adds foreign key constraint to goods_receipts.id.
  - Adds indexes on match_status, payment_status, goods_receipt_id, po_id.

All tenant-scoped tables preserve RLS and updated_at triggers.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extend spend_records for Phase 4 Invoice & 3-Way Matching ─────────────
    op.add_column("spend_records", sa.Column("invoice_date", sa.Date(), nullable=True))
    op.add_column("spend_records", sa.Column("due_date", sa.Date(), nullable=True))
    
    op.add_column(
        "spend_records",
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"),
    )
    op.create_index("ix_spend_records_payment_status", "spend_records", ["payment_status"])

    op.add_column(
        "spend_records",
        sa.Column("match_status", sa.String(20), nullable=False, server_default="unmatched"),
    )
    op.create_index("ix_spend_records_match_status", "spend_records", ["match_status"])

    op.add_column(
        "spend_records",
        sa.Column(
            "match_exceptions",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    op.add_column(
        "spend_records",
        sa.Column(
            "goods_receipt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("goods_receipts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_spend_records_goods_receipt_id",
        "spend_records",
        ["goods_receipt_id"],
    )

    op.add_column("spend_records", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column(
        "spend_records",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "spend_records",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "spend_records",
        sa.Column(
            "line_items",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("spend_records", sa.Column("notes", sa.Text(), nullable=True))

    op.create_index("ix_spend_records_po_id", "spend_records", ["po_id"])
    op.create_index("ix_spend_records_invoice_number", "spend_records", ["invoice_number"])


def downgrade() -> None:
    op.drop_index("ix_spend_records_invoice_number", table_name="spend_records")
    op.drop_index("ix_spend_records_po_id", table_name="spend_records")
    op.drop_column("spend_records", "notes")
    op.drop_column("spend_records", "line_items")
    op.drop_column("spend_records", "paid_at")
    op.drop_column("spend_records", "approved_at")
    op.drop_column("spend_records", "approved_by")
    op.drop_index("ix_spend_records_goods_receipt_id", table_name="spend_records")
    op.drop_column("spend_records", "goods_receipt_id")
    op.drop_column("spend_records", "match_exceptions")
    op.drop_index("ix_spend_records_match_status", table_name="spend_records")
    op.drop_column("spend_records", "match_status")
    op.drop_index("ix_spend_records_payment_status", table_name="spend_records")
    op.drop_column("spend_records", "payment_status")
    op.drop_column("spend_records", "due_date")
    op.drop_column("spend_records", "invoice_date")
