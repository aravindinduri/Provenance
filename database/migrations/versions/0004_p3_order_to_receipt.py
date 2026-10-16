"""Phase 3 — Order-to-Receipt (PO Lifecycle, Goods Receipt Notes)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15

Covers Phase 3 of the procurement architecture:
  - Extends purchase_orders table with full lifecycle fields:
      status, approved_by, approved_at, sent_at, acknowledged_at,
      expected_delivery_date, delivery_address, payment_terms, delivery_terms,
      notes, material_request_id, rfx_event_id, rfx_response_id.
  - Creates goods_receipts table for Goods Receipt Notes (GRN):
      id, org_id, grn_number, purchase_order_id, received_date, received_by,
      status, line_items, delivery_note_ref, carrier, notes, audit mixin, soft delete.

All tenant-scoped tables get RLS. All AuditMixin tables get updated_at trigger.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_updated_at_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def _drop_updated_at_trigger(table: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};")


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation ON {table}
          USING (org_id = current_setting('app.current_org_id', TRUE)::uuid);
        """
    )


def _disable_rls(table: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")


def upgrade() -> None:
    # ── 1. Extend purchase_orders ─────────────────────────────────────────────
    op.add_column(
        "purchase_orders",
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
    )
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    op.add_column("purchase_orders", sa.Column("approved_by", sa.String(), nullable=True))
    op.add_column(
        "purchase_orders",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("expected_delivery_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("delivery_address", postgresql.JSONB(), nullable=True),
    )
    op.add_column("purchase_orders", sa.Column("payment_terms", sa.Text(), nullable=True))
    op.add_column("purchase_orders", sa.Column("delivery_terms", sa.Text(), nullable=True))
    op.add_column("purchase_orders", sa.Column("notes", sa.Text(), nullable=True))

    op.add_column(
        "purchase_orders",
        sa.Column(
            "material_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_purchase_orders_material_request_id",
        "purchase_orders",
        ["material_request_id"],
    )

    op.add_column(
        "purchase_orders",
        sa.Column(
            "rfx_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rfx_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_purchase_orders_rfx_event_id", "purchase_orders", ["rfx_event_id"])

    op.add_column(
        "purchase_orders",
        sa.Column(
            "rfx_response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rfx_responses.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_purchase_orders_rfx_response_id",
        "purchase_orders",
        ["rfx_response_id"],
    )

    # ── 2. Create goods_receipts ──────────────────────────────────────────────
    op.create_table(
        "goods_receipts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("grn_number", sa.Text(), nullable=False),
        sa.Column(
            "purchase_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("received_by", sa.String(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "line_items",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("delivery_note_ref", sa.Text(), nullable=True),
        sa.Column("carrier", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.UniqueConstraint("org_id", "grn_number", name="uq_goods_receipt_grn_number"),
    )
    op.create_index("ix_goods_receipts_org_id", "goods_receipts", ["org_id"])
    op.create_index("ix_goods_receipts_purchase_order_id", "goods_receipts", ["purchase_order_id"])
    op.create_index("ix_goods_receipts_status", "goods_receipts", ["status"])
    _create_updated_at_trigger("goods_receipts")
    _enable_rls("goods_receipts")


def downgrade() -> None:
    _drop_updated_at_trigger("goods_receipts")
    _disable_rls("goods_receipts")
    op.drop_table("goods_receipts")

    op.drop_index("ix_purchase_orders_rfx_response_id", table_name="purchase_orders")
    op.drop_column("purchase_orders", "rfx_response_id")
    op.drop_index("ix_purchase_orders_rfx_event_id", table_name="purchase_orders")
    op.drop_column("purchase_orders", "rfx_event_id")
    op.drop_index("ix_purchase_orders_material_request_id", table_name="purchase_orders")
    op.drop_column("purchase_orders", "material_request_id")
    op.drop_column("purchase_orders", "notes")
    op.drop_column("purchase_orders", "delivery_terms")
    op.drop_column("purchase_orders", "payment_terms")
    op.drop_column("purchase_orders", "delivery_address")
    op.drop_column("purchase_orders", "expected_delivery_date")
    op.drop_column("purchase_orders", "acknowledged_at")
    op.drop_column("purchase_orders", "sent_at")
    op.drop_column("purchase_orders", "approved_at")
    op.drop_column("purchase_orders", "approved_by")
    op.drop_index("ix_purchase_orders_status", table_name="purchase_orders")
    op.drop_column("purchase_orders", "status")
