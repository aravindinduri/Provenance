"""Phase 1 — Items, Material Requests, Approval Engine

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13

Covers Phase 1 of the procurement architecture:
  - items (material master catalog)
  - material_requests (purchase requisitions)
  - material_request_items (line items)
  - approval_workflows (generic approval tracking)
  - approval_steps (individual decisions)
  - approval_rules (delegation of authority)

All tenant-scoped tables get RLS. All AuditMixin tables get updated_at trigger.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Helpers (mirrors 0001 pattern)
# ---------------------------------------------------------------------------


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


_P1_AUDIT_TABLES = [
    "items",
    "material_requests",
    "material_request_items",
    "approval_workflows",
    "approval_steps",
    "approval_rules",
]

_P1_RLS_TABLES = [
    "items",
    "material_requests",
    "material_request_items",
    "approval_workflows",
    "approval_steps",
    "approval_rules",
]


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ── items ─────────────────────────────────────────────────────────────────
    op.create_table(
        "items",
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
        sa.Column("item_code", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.Text, nullable=True),
        sa.Column("unit_of_measure", sa.String(20), nullable=True),
        sa.Column("default_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column(
            "preferred_supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("lead_time_days", sa.Integer, nullable=True),
        sa.Column("min_order_qty", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
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
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("org_id", "item_code", name="uq_item_code_per_org"),
    )
    op.create_index("ix_items_org_id", "items", ["org_id"])
    op.create_index("ix_items_is_active", "items", ["is_active"])

    # ── material_requests ──────────────────────────────────────────────────────
    op.create_table(
        "material_requests",
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
        sa.Column("mr_number", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column(
            "status", sa.String(30), nullable=False, server_default="draft"
        ),
        sa.Column("requested_by", sa.String, nullable=True),
        sa.Column("required_by_date", sa.Date, nullable=True),
        sa.Column("priority", sa.String(10), nullable=True, server_default="medium"),
        sa.Column("department", sa.Text, nullable=True),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("total_estimated_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
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
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("org_id", "mr_number", name="uq_mr_number_per_org"),
    )
    op.create_index("ix_material_requests_org_id", "material_requests", ["org_id"])
    op.create_index("ix_material_requests_status", "material_requests", ["status"])

    # ── material_request_items ─────────────────────────────────────────────────
    op.create_table(
        "material_request_items",
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
            "material_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_of_measure", sa.String(20), nullable=True),
        sa.Column("estimated_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column(
            "preferred_supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_mr_items_material_request_id",
        "material_request_items",
        ["material_request_id"],
    )
    op.create_index("ix_mr_items_org_id", "material_request_items", ["org_id"])

    # ── approval_workflows ─────────────────────────────────────────────────────
    op.create_table(
        "approval_workflows",
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
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column("initiated_by", sa.String, nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
    )
    op.create_index("ix_approval_workflows_org_id", "approval_workflows", ["org_id"])
    op.create_index(
        "ix_approval_workflows_document",
        "approval_workflows",
        ["document_type", "document_id"],
    )

    # ── approval_steps ─────────────────────────────────────────────────────────
    op.create_table(
        "approval_steps",
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
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("approver_id", sa.String, nullable=True),
        sa.Column("approver_role", sa.String(50), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("delegated_to", sa.String, nullable=True),
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
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
    )
    op.create_index("ix_approval_steps_workflow_id", "approval_steps", ["workflow_id"])
    op.create_index("ix_approval_steps_org_id", "approval_steps", ["org_id"])

    # ── approval_rules ─────────────────────────────────────────────────────────
    op.create_table(
        "approval_rules",
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
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("min_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("max_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("required_role", sa.String(50), nullable=False),
        sa.Column("auto_approve_below", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("priority", sa.Integer, nullable=False, server_default="10"),
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
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
    )
    op.create_index("ix_approval_rules_org_id", "approval_rules", ["org_id"])

    # ── RLS ────────────────────────────────────────────────────────────────────
    for table in _P1_RLS_TABLES:
        _enable_rls(table)

    # ── updated_at triggers ────────────────────────────────────────────────────
    for table in _P1_AUDIT_TABLES:
        _create_updated_at_trigger(table)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    for table in reversed(_P1_AUDIT_TABLES):
        _drop_updated_at_trigger(table)

    for table in reversed(_P1_RLS_TABLES):
        _disable_rls(table)

    op.drop_table("approval_rules")
    op.drop_table("approval_steps")
    op.drop_table("approval_workflows")
    op.drop_table("material_request_items")
    op.drop_table("material_requests")
    op.drop_table("items")
