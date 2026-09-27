"""Initial schema — all tables, indexes, RLS, triggers, partitioning

Revision ID: 0001
Revises:
Create Date: 2026-09-27

Covers Phase 2 of the implementation plan:
  - All domain tables from Part M of the architecture spec
  - GIN trigram index on companies.name_norm
  - GIN full-text indexes on events.summary and document_chunks.content
  - Partial indexes on supplier_relationships (WHERE valid_to IS NULL)
  - Partial HNSW index on embeddings (WHERE model = 'voyage-3')
  - RLS policies on all tenant-scoped tables
  - set_updated_at() trigger on every table that carries updated_at
  - alert_must_have_evidence deferred trigger (engineering rule 9)
  - audit_logs range partitioning by month
  - REVOKE UPDATE/DELETE on audit_logs from provenance_app role
  - app_role 'provenance_app' created if absent
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_updated_at_trigger(table: str) -> None:
    """Attach the set_updated_at trigger to a table."""
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def _drop_updated_at_trigger(table: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};")


# Tables that carry updated_at (AuditMixin)
_AUDIT_TABLES = [
    "organizations",
    "organization_members",
    "companies",
    "company_identifiers",
    "company_aliases",
    "entity_resolution_reviews",
    "supplier_relationships",
    "company_locations",
    "data_sources",
    "source_records",
    "events",
    "event_entities",
    "risk_model_versions",
    "risk_assessments",
    "alerts",
    "uploaded_documents",
    "contracts",
    "purchase_orders",
    "spend_records",
    "spend_leakage_findings",
    "documents",
    "agent_runs",
]

# Tenant-scoped tables that get RLS
_RLS_TABLES = [
    "supplier_relationships",
    "risk_assessments",
    "alerts",
    "uploaded_documents",
    "contracts",
    "purchase_orders",
    "spend_records",
    "spend_leakage_findings",
    "notification_preferences",
    "notifications",
    "category_index_mappings",
    "supplier_price_claims",
]


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ── 0. App role (idempotent) ─────────────────────────────────────────────
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'provenance_app') THEN
                CREATE ROLE provenance_app;
            END IF;
        END
        $$;
        """
    )

    # ── 1. set_updated_at() function ─────────────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;
        """
    )

    # ── 2. companies (global, no RLS) ────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("name_norm", sa.Text(), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("jurisdiction", sa.String(100), nullable=True),
        sa.Column("legal_form", sa.String(100), nullable=True),
        sa.Column("entity_status", sa.String(50), nullable=True),
        sa.Column("primary_domain", sa.String(255), nullable=True),
        sa.Column("industry_codes", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("registered_address", postgresql.JSONB(), nullable=True),
        sa.Column("hq_address", postgresql.JSONB(), nullable=True),
        sa.Column("data_source", sa.String(50), nullable=True),
        sa.Column("enrichment_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), server_default=sa.text("1.0"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # GIN trigram index for fuzzy name matching (Stage 5 of ER cascade)
    op.execute(
        "CREATE INDEX ix_companies_name_norm_trgm ON companies "
        "USING gin (name_norm gin_trgm_ops);"
    )
    op.create_index("ix_companies_country", "companies", ["country"])
    op.create_index("ix_companies_primary_domain", "companies", ["primary_domain"])
    op.create_index(
        "ix_companies_deleted",
        "companies",
        ["id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    _create_updated_at_trigger("companies")

    # ── 3. company_identifiers ───────────────────────────────────────────────
    op.create_table(
        "company_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_type", sa.String(30), nullable=False),
        sa.Column("identifier_value", sa.Text(), nullable=False),
        sa.Column("issuing_country", sa.String(2), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier_type", "identifier_value", name="uq_company_identifier"),
    )
    op.create_index("ix_company_identifiers_company_id", "company_identifiers", ["company_id"])
    _create_updated_at_trigger("company_identifiers")

    # ── 4. company_aliases ───────────────────────────────────────────────────
    op.create_table(
        "company_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("alias_norm", sa.Text(), nullable=False),
        sa.Column("alias_type", sa.String(50), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "alias_norm", name="uq_company_alias_norm"),
    )
    op.create_index("ix_company_aliases_company_id", "company_aliases", ["company_id"])
    _create_updated_at_trigger("company_aliases")

    # ── 5. locations (global reference data) ─────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("lon", sa.Numeric(9, 6), nullable=True),
        sa.Column("geohash", sa.String(12), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_country", "locations", ["country"])

    # ── 6. organizations ─────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("clerk_org_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("subscription_tier", sa.String(50), server_default="free", nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("monthly_token_budget", sa.BigInteger(), server_default=sa.text("5000000"), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_org_id"),
        sa.UniqueConstraint("slug"),
    )
    _create_updated_at_trigger("organizations")

    # ── 7. organization_members ──────────────────────────────────────────────
    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(50), server_default="org_user", nullable=False),
        sa.Column("persona", sa.String(50), nullable=True),
        sa.Column("assigned_categories", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )
    op.create_index("ix_organization_members_org_id", "organization_members", ["org_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    _create_updated_at_trigger("organization_members")

    # ── 8. entity_resolution_reviews ─────────────────────────────────────────
    op.create_table(
        "entity_resolution_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.Column("context", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("candidates", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("suggested_company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("ai_reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("resolved_company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggested_company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_er_reviews_org_id", "entity_resolution_reviews", ["org_id"])
    op.create_index("ix_er_reviews_status", "entity_resolution_reviews", ["status"])
    _create_updated_at_trigger("entity_resolution_reviews")

    # ── 9. data_sources ──────────────────────────────────────────────────────
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_key", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("auth_type", sa.String(30), nullable=True),
        sa.Column("reliability", sa.String(10), server_default="high", nullable=False),
        sa.Column("license_terms", sa.Text(), nullable=True),
        sa.Column("terms_verified_at", sa.Date(), nullable=True),
        sa.Column("coverage_notes", sa.Text(), nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(20), server_default="healthy", nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    _create_updated_at_trigger("data_sources")

    # ── 10. source_records ───────────────────────────────────────────────────
    op.create_table(
        "source_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_s3_key", sa.Text(), nullable=False),
        sa.Column("normalized", postgresql.JSONB(), nullable=False),
        sa.Column("source_type", sa.String(10), nullable=True),
        sa.Column("reliability", sa.String(10), nullable=True),
        sa.Column("language", sa.String(2), nullable=True),
        sa.Column("processing_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("seen_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_source_record_ext_id"),
        sa.UniqueConstraint("source_id", "content_hash", name="uq_source_record_hash"),
    )
    op.create_index("ix_source_records_source_id", "source_records", ["source_id"])
    op.create_index("ix_source_records_processing_status", "source_records", ["processing_status"])
    _create_updated_at_trigger("source_records")

    # ── 11. source_record_versions ───────────────────────────────────────────
    op.create_table(
        "source_record_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("normalized", postgresql.JSONB(), nullable=False),
        sa.Column("raw_s3_key", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_record_id", "version", name="uq_source_record_version"),
    )
    op.create_index("ix_source_record_versions_rec_id", "source_record_versions", ["source_record_id"])

    # ── 12. dead_letter_queue ────────────────────────────────────────────────
    op.create_table(
        "dead_letter_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("traceback", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(20), server_default="failed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replayed_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dlq_task_name", "dead_letter_queue", ["task_name"])
    op.create_index("ix_dlq_status", "dead_letter_queue", ["status"])

    # ── 13. events (global) ──────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_cluster_key", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("jurisdictions", postgresql.ARRAY(sa.String(2)), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("affected_materials", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("affected_hs_codes", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity_signal", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("corroboration_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extracted_by_model", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["superseded_by"], ["events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_cluster_key", "events", ["event_cluster_key"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_status", "events", ["status"])
    # GIN index on jurisdictions array
    op.execute(
        "CREATE INDEX ix_events_jurisdictions_gin ON events "
        "USING gin (jurisdictions);"
    )
    # GIN full-text index on summary
    op.execute(
        "CREATE INDEX ix_events_summary_fts ON events "
        "USING gin (to_tsvector('english', summary));"
    )
    _create_updated_at_trigger("events")

    # ── 14. event_source_records (M2M) ───────────────────────────────────────
    op.create_table(
        "event_source_records",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "source_record_id"),
        sa.UniqueConstraint("event_id", "source_record_id", name="uq_event_source_record"),
    )

    # ── 15. event_entities ───────────────────────────────────────────────────
    op.create_table(
        "event_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_mention", sa.Text(), nullable=False),
        sa.Column("role", sa.String(30), nullable=True),
        sa.Column("resolution_confidence", sa.Integer(), nullable=True),
        sa.Column("resolution_method", sa.String(30), nullable=True),
        sa.Column("evidence_span", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_entities_event_id", "event_entities", ["event_id"])
    op.create_index("ix_event_entities_company_id", "event_entities", ["company_id"])
    _create_updated_at_trigger("event_entities")

    # ── 16. supplier_relationships (tenant-scoped, RLS) ───────────────────────
    op.create_table(
        "supplier_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=True),
        sa.Column("criticality", sa.SmallInteger(), nullable=True),
        sa.Column("annual_spend_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("single_source", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), server_default=sa.text("1.0"), nullable=False),
        sa.Column("source", sa.String(30), server_default="user_declared", nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valid_from", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("inherited_from_edge_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.CheckConstraint(
            "to_company_id IS NOT NULL OR to_org_id IS NOT NULL",
            name="ck_sr_has_target",
        ),
        sa.CheckConstraint("criticality BETWEEN 1 AND 5", name="ck_sr_criticality_range"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inherited_from_edge_id"], ["supplier_relationships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Partial indexes on active edges (valid_to IS NULL) — the primary traversal path
    op.create_index(
        "ix_sr_org_from_active",
        "supplier_relationships",
        ["org_id", "from_company_id"],
        postgresql_where=sa.text("valid_to IS NULL"),
    )
    op.create_index(
        "ix_sr_org_to_active",
        "supplier_relationships",
        ["org_id", "to_company_id"],
        postgresql_where=sa.text("valid_to IS NULL"),
    )
    _create_updated_at_trigger("supplier_relationships")

    # ── 17. company_locations ────────────────────────────────────────────────
    op.create_table(
        "company_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_type", sa.String(30), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), server_default=sa.text("1.0"), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_locations_company_id", "company_locations", ["company_id"])
    op.create_index("ix_company_locations_location_id", "company_locations", ["location_id"])
    _create_updated_at_trigger("company_locations")

    # ── 18. risk_model_versions ──────────────────────────────────────────────
    op.create_table(
        "risk_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    _create_updated_at_trigger("risk_model_versions")

    # ── 19. risk_assessments (tenant-scoped, RLS) ────────────────────────────
    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impact_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("severity_band", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("graph_path", postgresql.JSONB(), nullable=False),
        sa.Column("path_depth", sa.SmallInteger(), nullable=True),
        sa.Column("path_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("completeness", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "event_id", "company_id", name="uq_risk_assessment"),
    )
    op.create_index("ix_risk_assessments_org_id", "risk_assessments", ["org_id"])
    op.create_index("ix_risk_assessments_event_id", "risk_assessments", ["event_id"])
    op.create_index("ix_risk_assessments_company_id", "risk_assessments", ["company_id"])
    _create_updated_at_trigger("risk_assessments")

    # ── 20. alerts (tenant-scoped, RLS) ──────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_assessment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("headline", sa.String(200), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("severity_band", sa.String(20), nullable=False),
        sa.Column("impact_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("needs_human_judgment", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("target_personas", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{risk_manager,category_manager}'::text[]"), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("explanation_model", sa.String(100), nullable=True),
        sa.Column("explanation_prompt_version", sa.String(50), nullable=True),
        sa.Column("first_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_event_id", "alerts", ["event_id"])
    op.create_index("ix_alerts_company_id", "alerts", ["company_id"])
    op.create_index("ix_alerts_severity_band", "alerts", ["severity_band"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_category", "alerts", ["category"])
    # Composite index for the primary list query: org → status + severity + created_at DESC
    op.create_index(
        "ix_alerts_org_status_severity",
        "alerts",
        ["org_id", "status", "severity_band", "created_at"],
    )
    _create_updated_at_trigger("alerts")

    # ── 21. documents (AI/RAG corpus) ────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("jurisdiction", sa.String(2), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(5), nullable=True),
        sa.Column("source_reliability", sa.String(10), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_org_id", "documents", ["org_id"])
    _create_updated_at_trigger("documents")

    # ── 22. document_chunks ──────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("section_path", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    # GIN full-text index — lexical side of hybrid retrieval
    op.execute(
        "CREATE INDEX ix_document_chunks_content_fts ON document_chunks "
        "USING gin (to_tsvector('english', content));"
    )

    # ── 23. alert_evidence (references document_chunks) ──────────────────────
    op.create_table(
        "alert_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_type", sa.String(10), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_evidence_alert_id", "alert_evidence", ["alert_id"])

    # ── 24. alert_actions ────────────────────────────────────────────────────
    op.create_table(
        "alert_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_actions_alert_id", "alert_actions", ["alert_id"])

    # ── 25. embeddings (pgvector) ────────────────────────────────────────────
    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        # Use vector type from pgvector — installed by init.sql
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "model", name="uq_embedding_chunk_model"),
    )
    op.create_index("ix_embeddings_chunk_id", "embeddings", ["chunk_id"])
    # Alter embedding column to the real pgvector type
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector(1024);")
    # Partial HNSW index — only for the current default model; model changes don't break it
    op.execute(
        "CREATE INDEX ix_embeddings_hnsw_voyage3 ON embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WHERE model = 'voyage-3';"
    )

    # ── 26. agent_runs ───────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_ref", postgresql.JSONB(), nullable=True),
        sa.Column("output_ref", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("langfuse_trace_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_org_id_created", "agent_runs", ["org_id", "created_at"])
    op.create_index("ix_agent_runs_agent_name_created", "agent_runs", ["agent_name", "created_at"])
    op.create_index("ix_agent_runs_workflow_run_id", "agent_runs", ["workflow_run_id"])

    # ── 27. uploaded_documents (tenant-scoped, RLS) ───────────────────────────
    op.create_table(
        "uploaded_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(30), nullable=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("parse_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("parse_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("parsed_payload", postgresql.JSONB(), nullable=True),
        sa.Column("parse_errors", postgresql.JSONB(), nullable=True),
        sa.Column("uploaded_by", sa.String(), nullable=True),
        sa.Column("virus_scan_status", sa.String(20), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "content_hash", name="uq_uploaded_doc"),
    )
    op.create_index("ix_uploaded_documents_org_id", "uploaded_documents", ["org_id"])
    op.create_index("ix_uploaded_documents_parse_status", "uploaded_documents", ["parse_status"])
    _create_updated_at_trigger("uploaded_documents")

    # ── 28. contracts (tenant-scoped, RLS) ───────────────────────────────────
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_number", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("renewal_terms", postgresql.JSONB(), nullable=True),
        sa.Column("agreed_unit_prices", postgresql.JSONB(), nullable=True),
        sa.Column("payment_terms", postgresql.JSONB(), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_document_id"], ["uploaded_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contracts_org_id", "contracts", ["org_id"])
    op.create_index("ix_contracts_company_id", "contracts", ["company_id"])
    _create_updated_at_trigger("contracts")

    # ── 29. purchase_orders (tenant-scoped, RLS) ─────────────────────────────
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("po_number", sa.Text(), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("line_items", postgresql.JSONB(), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_document_id"], ["uploaded_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "po_number", name="uq_purchase_order"),
    )
    op.create_index("ix_purchase_orders_org_id", "purchase_orders", ["org_id"])
    op.create_index("ix_purchase_orders_company_id", "purchase_orders", ["company_id"])
    _create_updated_at_trigger("purchase_orders")

    # ── 30. spend_records (tenant-scoped, RLS) ───────────────────────────────
    op.create_table(
        "spend_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("po_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_number", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("spend_date", sa.Date(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_document_id"], ["uploaded_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "company_id", "invoice_number", name="uq_spend_record"),
    )
    op.create_index("ix_spend_records_org_id", "spend_records", ["org_id"])
    op.create_index("ix_spend_records_company_id", "spend_records", ["company_id"])
    _create_updated_at_trigger("spend_records")

    # ── 31. spend_leakage_findings (tenant-scoped, RLS) ───────────────────────
    op.create_table(
        "spend_leakage_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(30), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("amount_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("regulatory_overlap", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("risk_assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_assessment_id"], ["risk_assessments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spend_leakage_org_id", "spend_leakage_findings", ["org_id"])
    op.create_index("ix_spend_leakage_company_id", "spend_leakage_findings", ["company_id"])
    op.create_index("ix_spend_leakage_regulatory_overlap", "spend_leakage_findings", ["regulatory_overlap"])
    op.create_index("ix_spend_leakage_status", "spend_leakage_findings", ["status"])
    _create_updated_at_trigger("spend_leakage_findings")

    # ── 32. notification_preferences (tenant-scoped, RLS) ────────────────────
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("min_severity", sa.String(20), nullable=True),
        sa.Column("digest_frequency", sa.String(20), nullable=True),
        sa.Column("categories", postgresql.JSONB(), nullable=True),
        sa.Column("quiet_hours", postgresql.JSONB(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", "channel", name="uq_notification_pref"),
    )
    op.create_index("ix_notification_prefs_org_id", "notification_preferences", ["org_id"])

    # ── 33. notifications (tenant-scoped, RLS) ────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_org_id", "notifications", ["org_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_alert_id", "notifications", ["alert_id"])

    # ── 34. notification_deliveries ──────────────────────────────────────────
    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_notification_delivery_idem"),
    )
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])

    # ── 35. audit_logs (append-only, range partitioned) ───────────────────────
    # Create as a partitioned table; the first monthly partition covers the
    # current month. A weekly maintenance job creates future partitions.
    op.execute(
        """
        CREATE TABLE audit_logs (
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            org_id      UUID REFERENCES organizations(id) ON DELETE SET NULL,
            user_id     TEXT,
            actor_type  TEXT NOT NULL DEFAULT 'user',
            action      TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            changes     JSONB,
            ip_address  INET,
            user_agent  TEXT,
            request_id  TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        ) PARTITION BY RANGE (created_at);
        """
    )
    # Create the first two monthly partitions (current + next month).
    # The weekly maintenance job keeps this rolling.
    op.execute(
        """
        CREATE TABLE audit_logs_2026_09 PARTITION OF audit_logs
            FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
        CREATE TABLE audit_logs_2026_10 PARTITION OF audit_logs
            FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
        CREATE TABLE audit_logs_2026_11 PARTITION OF audit_logs
            FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
        CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;
        """
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_org_id ON audit_logs (org_id);"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_action ON audit_logs (action);"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);"
    )
    op.execute(
        "CREATE INDEX ix_audit_logs_request_id ON audit_logs (request_id);"
    )

    # ── 36. alert_must_have_evidence — deferred trigger ───────────────────────
    # Raises if a transaction commits an alert that has no evidence rows.
    # Deferred so that the alert and its first evidence row can be inserted
    # in the same transaction without ordering constraints.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION check_alert_has_evidence()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM alert_evidence WHERE alert_id = NEW.id
            ) THEN
                RAISE EXCEPTION
                    'alert % has no evidence rows (engineering rule 9)', NEW.id;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER alert_must_have_evidence
        AFTER INSERT ON alerts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION check_alert_has_evidence();
        """
    )

    # ── 37. RLS policies on all tenant-scoped tables ──────────────────────────
    # Pattern: ENABLE RLS + a USING policy that compares org_id against the
    # session-local setting 'app.current_org_id', set by TenantContextMiddleware.
    #
    # IMPORTANT: companies, events, source_records, data_sources are intentionally
    # NOT listed here — they are global public reference data. Do not add them.
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (org_id = current_setting('app.current_org_id', true)::uuid);
            """
        )

    # ── 38. Revoke destructive privileges on audit_logs ───────────────────────
    # The application role must never be able to UPDATE or DELETE audit rows.
    # INSERT and SELECT are granted so the app can write and read logs.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'provenance_app') THEN
                REVOKE UPDATE, DELETE ON audit_logs FROM provenance_app;
                GRANT INSERT, SELECT ON audit_logs TO provenance_app;
            END IF;
        END
        $$;
        """
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # Drop in reverse dependency order

    # Triggers first
    for table in reversed(_AUDIT_TABLES):
        _drop_updated_at_trigger(table)

    op.execute("DROP TRIGGER IF EXISTS alert_must_have_evidence ON alerts;")
    op.execute("DROP FUNCTION IF EXISTS check_alert_has_evidence();")

    # Tables (reverse creation order)
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE;")
    op.drop_table("notification_deliveries")
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
    op.drop_table("spend_leakage_findings")
    op.drop_table("spend_records")
    op.drop_table("purchase_orders")
    op.drop_table("contracts")
    op.drop_table("uploaded_documents")
    op.drop_table("agent_runs")
    op.drop_table("embeddings")
    op.drop_table("alert_actions")
    op.drop_table("alert_evidence")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("alerts")
    op.drop_table("risk_assessments")
    op.drop_table("risk_model_versions")
    op.drop_table("company_locations")
    op.drop_table("supplier_relationships")
    op.drop_table("event_entities")
    op.drop_table("event_source_records")
    op.drop_table("events")
    op.drop_table("dead_letter_queue")
    op.drop_table("source_record_versions")
    op.drop_table("source_records")
    op.drop_table("data_sources")
    op.drop_table("entity_resolution_reviews")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    op.drop_table("locations")
    op.drop_table("company_aliases")
    op.drop_table("company_identifiers")
    op.drop_table("companies")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
