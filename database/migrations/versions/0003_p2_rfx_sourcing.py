"""Phase 2 — Sourcing (RFQ/RFP, Invitations, Quotations, Bid Comparison)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15

Covers Phase 2 of the procurement architecture:
  - rfx_events (sourcing events: RFI, RFQ, RFP, RFT)
  - rfx_invitations (supplier invitations to sourcing events)
  - rfx_responses (supplier quotations and proposals)

All tenant-scoped tables get RLS. All AuditMixin tables get updated_at trigger.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
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


_P2_TABLES = [
    "rfx_events",
    "rfx_invitations",
    "rfx_responses",
]


def upgrade() -> None:
    # ── 1. rfx_events ────────────────────────────────────────────────────────
    op.create_table(
        "rfx_events",
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
        sa.Column("rfx_number", sa.Text(), nullable=False),
        sa.Column("rfx_type", sa.String(10), nullable=False, server_default="rfq"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "material_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column(
            "evaluation_criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "awarded_supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
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
        sa.UniqueConstraint("org_id", "rfx_number", name="uq_rfx_number_per_org"),
    )
    op.create_index("ix_rfx_events_org_id", "rfx_events", ["org_id"])
    op.create_index("ix_rfx_events_status", "rfx_events", ["status"])
    op.create_index("ix_rfx_events_material_request_id", "rfx_events", ["material_request_id"])
    op.create_index("ix_rfx_events_deleted", "rfx_events", ["id"], postgresql_where=sa.text("deleted_at IS NULL"))
    _create_updated_at_trigger("rfx_events")
    _enable_rls("rfx_events")

    # ── 2. rfx_invitations ───────────────────────────────────────────────────
    op.create_table(
        "rfx_invitations",
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
        sa.Column(
            "rfx_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rfx_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="invited"),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
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
        sa.UniqueConstraint("rfx_event_id", "supplier_id", name="uq_rfx_event_supplier_invitation"),
    )
    op.create_index("ix_rfx_invitations_org_id", "rfx_invitations", ["org_id"])
    op.create_index("ix_rfx_invitations_rfx_event_id", "rfx_invitations", ["rfx_event_id"])
    op.create_index("ix_rfx_invitations_supplier_id", "rfx_invitations", ["supplier_id"])
    op.create_index("ix_rfx_invitations_deleted", "rfx_invitations", ["id"], postgresql_where=sa.text("deleted_at IS NULL"))
    _create_updated_at_trigger("rfx_invitations")
    _enable_rls("rfx_invitations")

    # ── 3. rfx_responses ─────────────────────────────────────────────────────
    op.create_table(
        "rfx_responses",
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
        sa.Column(
            "rfx_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rfx_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("response_number", sa.Text(), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "line_items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "evaluation_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("validity_date", sa.Date(), nullable=True),
        sa.Column("payment_terms", sa.Text(), nullable=True),
        sa.Column("delivery_terms", sa.Text(), nullable=True),
        sa.Column(
            "attachments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("is_best_offer", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("uploaded_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
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
        sa.UniqueConstraint("org_id", "response_number", name="uq_rfx_response_number_per_org"),
    )
    op.create_index("ix_rfx_responses_org_id", "rfx_responses", ["org_id"])
    op.create_index("ix_rfx_responses_rfx_event_id", "rfx_responses", ["rfx_event_id"])
    op.create_index("ix_rfx_responses_supplier_id", "rfx_responses", ["supplier_id"])
    op.create_index("ix_rfx_responses_deleted", "rfx_responses", ["id"], postgresql_where=sa.text("deleted_at IS NULL"))
    _create_updated_at_trigger("rfx_responses")
    _enable_rls("rfx_responses")


def downgrade() -> None:
    for table in reversed(_P2_TABLES):
        _disable_rls(table)
        _drop_updated_at_trigger(table)
        op.drop_table(table)
