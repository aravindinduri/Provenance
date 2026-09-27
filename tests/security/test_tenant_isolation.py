"""
tests/security/test_tenant_isolation.py
BLOCKING in CI — the build must not ship if any of these fail.

Verifies:
1. RLS blocks cross-tenant reads on supplier_relationships
2. RLS blocks cross-tenant reads on risk_assessments
3. RLS blocks cross-tenant reads on alerts
4. RLS blocks cross-tenant reads on uploaded_documents
5. RLS blocks cross-tenant reads on spend_leakage_findings
6. companies table is NOT RLS-restricted (global reference data)
7. UNIQUE (org_id, event_id, company_id) on risk_assessments is idempotent
8. alert_must_have_evidence deferred trigger fires on bare INSERT
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import make_company, make_edge, make_org


# ---------------------------------------------------------------------------
# Helper — set RLS context
# ---------------------------------------------------------------------------

def _set_org(session, org_id: uuid.UUID) -> None:
    """Set the tenant context that RLS policies read."""
    session.execute(
        text("SET LOCAL app.current_org_id = :oid"),
        {"oid": str(org_id)},
    )


def _enable_rls(session) -> None:
    session.execute(text("SET LOCAL row_security = on;"))


# ---------------------------------------------------------------------------
# 1–5. RLS isolation: tenant A cannot read tenant B's rows
# ---------------------------------------------------------------------------

class TestSupplierRelationshipsRLS:
    def test_tenant_a_cannot_read_tenant_b_edges(self, db_session):
        """
        Create two tenants each with one supplier edge.
        Authenticate as Tenant A and assert Tenant B's edge is invisible.
        """
        # Setup (RLS off — fixture default)
        co_a = make_company(db_session, name_norm="co alpha")
        co_b = make_company(db_session, name_norm="co beta")
        org_a = make_org(db_session, slug="org-alpha", company_id=co_a)
        org_b = make_org(db_session, slug="org-beta", company_id=co_b)

        supplier_a = make_company(db_session, name_norm="supplier alpha cn", country="CN")
        supplier_b = make_company(db_session, name_norm="supplier beta de", country="DE")

        edge_a = make_edge(db_session, org_id=org_a, from_company_id=supplier_a, to_org_id=org_a)
        edge_b = make_edge(db_session, org_id=org_b, from_company_id=supplier_b, to_org_id=org_b)
        db_session.flush()

        # Switch to RLS-on mode and authenticate as Tenant A
        _enable_rls(db_session)
        _set_org(db_session, org_a)

        rows = db_session.execute(
            text("SELECT id FROM supplier_relationships")
        ).fetchall()
        visible_ids = {r[0] for r in rows}

        assert edge_a in visible_ids, "Tenant A's own edge must be visible"
        assert edge_b not in visible_ids, "Tenant B's edge must NOT be visible to Tenant A"

    def test_tenant_b_cannot_read_tenant_a_edges(self, db_session):
        co_a = make_company(db_session, name_norm="co gamma")
        co_b = make_company(db_session, name_norm="co delta")
        org_a = make_org(db_session, slug="org-gamma", company_id=co_a)
        org_b = make_org(db_session, slug="org-delta", company_id=co_b)

        supplier_a = make_company(db_session, name_norm="supplier gamma", country="JP")
        edge_a = make_edge(db_session, org_id=org_a, from_company_id=supplier_a, to_org_id=org_a)
        db_session.flush()

        _enable_rls(db_session)
        _set_org(db_session, org_b)  # <-- different tenant

        rows = db_session.execute(
            text("SELECT id FROM supplier_relationships")
        ).fetchall()
        assert edge_a not in {r[0] for r in rows}


class TestRiskAssessmentsRLS:
    def test_cross_tenant_risk_assessment_hidden(self, db_session):
        co_a = make_company(db_session, name_norm="risk co a")
        co_b = make_company(db_session, name_norm="risk co b")
        org_a = make_org(db_session, slug="risk-org-a", company_id=co_a)
        org_b = make_org(db_session, slug="risk-org-b", company_id=co_b)

        event_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO events
                    (id, event_cluster_key, event_type, summary, created_at, updated_at)
                VALUES
                    (:id, 'test-cluster', 'export_restriction', 'Test event', NOW(), NOW())
                """
            ),
            {"id": event_id},
        )

        ra_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO risk_assessments
                    (id, org_id, event_id, company_id, impact_score, severity_band,
                     confidence, factors, graph_path, model_version, created_at, updated_at)
                VALUES
                    (:id, :org_id, :event_id, :company_id, 72.5, 'HIGH',
                     0.88, '{}'::jsonb, '[]'::jsonb, 'v1', NOW(), NOW())
                """
            ),
            {"id": ra_id, "org_id": org_a, "event_id": event_id, "company_id": co_a},
        )
        db_session.flush()

        _enable_rls(db_session)
        _set_org(db_session, org_b)

        rows = db_session.execute(text("SELECT id FROM risk_assessments")).fetchall()
        assert ra_id not in {r[0] for r in rows}, \
            "Org B must not see Org A's risk assessments"


class TestAlertsRLS:
    def test_cross_tenant_alert_hidden(self, db_session):
        co_a = make_company(db_session, name_norm="alert co a")
        co_b = make_company(db_session, name_norm="alert co b")
        org_a = make_org(db_session, slug="alert-org-a", company_id=co_a)
        org_b = make_org(db_session, slug="alert-org-b", company_id=co_b)

        event_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO events (id, event_cluster_key, event_type, summary, created_at, updated_at)
                VALUES (:id, 'alert-cluster', 'sanction_designation', 'Sanction test', NOW(), NOW())
                """
            ),
            {"id": event_id},
        )
        ra_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO risk_assessments
                    (id, org_id, event_id, company_id, impact_score, severity_band,
                     confidence, factors, graph_path, model_version, created_at, updated_at)
                VALUES (:id, :oid, :eid, :cid, 80.0, 'CRITICAL', 0.9, '{}'::jsonb, '[]'::jsonb, 'v1', NOW(), NOW())
                """
            ),
            {"id": ra_id, "oid": org_a, "eid": event_id, "cid": co_a},
        )

        alert_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO alerts
                    (id, org_id, risk_assessment_id, event_id, company_id,
                     headline, severity_band, impact_score, confidence,
                     created_at, updated_at)
                VALUES
                    (:id, :oid, :raid, :eid, :cid,
                     'Test alert', 'CRITICAL', 80.0, 0.9,
                     NOW(), NOW())
                """
            ),
            {"id": alert_id, "oid": org_a, "raid": ra_id, "eid": event_id, "cid": co_a},
        )
        # Insert evidence so the deferred trigger is satisfied
        db_session.execute(
            text(
                """
                INSERT INTO alert_evidence (id, alert_id, evidence_type, display_order)
                VALUES (gen_random_uuid(), :aid, 'score_factor', 0)
                """
            ),
            {"aid": alert_id},
        )
        db_session.flush()

        _enable_rls(db_session)
        _set_org(db_session, org_b)

        rows = db_session.execute(text("SELECT id FROM alerts")).fetchall()
        assert alert_id not in {r[0] for r in rows}, \
            "Org B must not see Org A's alerts"


class TestUploadedDocumentsRLS:
    def test_cross_tenant_document_hidden(self, db_session):
        co_a = make_company(db_session, name_norm="doc co a")
        co_b = make_company(db_session, name_norm="doc co b")
        org_a = make_org(db_session, slug="doc-org-a", company_id=co_a)
        org_b = make_org(db_session, slug="doc-org-b", company_id=co_b)

        doc_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO uploaded_documents
                    (id, org_id, filename, s3_key, content_hash, created_at, updated_at)
                VALUES
                    (:id, :oid, 'invoice.pdf', 's3://bucket/key', 'abc123', NOW(), NOW())
                """
            ),
            {"id": doc_id, "oid": org_a},
        )
        db_session.flush()

        _enable_rls(db_session)
        _set_org(db_session, org_b)

        rows = db_session.execute(text("SELECT id FROM uploaded_documents")).fetchall()
        assert doc_id not in {r[0] for r in rows}


class TestSpendLeakageRLS:
    def test_cross_tenant_finding_hidden(self, db_session):
        co_a = make_company(db_session, name_norm="spend co a")
        co_b = make_company(db_session, name_norm="spend co b")
        org_a = make_org(db_session, slug="spend-org-a", company_id=co_a)
        org_b = make_org(db_session, slug="spend-org-b", company_id=co_b)

        finding_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO spend_leakage_findings
                    (id, org_id, finding_type, evidence, created_at, updated_at)
                VALUES
                    (:id, :oid, 'duplicate_payment', '{}'::jsonb, NOW(), NOW())
                """
            ),
            {"id": finding_id, "oid": org_a},
        )
        db_session.flush()

        _enable_rls(db_session)
        _set_org(db_session, org_b)

        rows = db_session.execute(text("SELECT id FROM spend_leakage_findings")).fetchall()
        assert finding_id not in {r[0] for r in rows}


# ---------------------------------------------------------------------------
# 6. companies is NOT RLS-restricted — must be cross-tenant readable
# ---------------------------------------------------------------------------

class TestCompaniesIsGlobal:
    def test_company_visible_across_tenants(self, db_session):
        """
        companies is public reference data. Both tenants must be able to read it
        regardless of the current org context.
        """
        co = make_company(db_session, name_norm="shared global corp")
        db_session.flush()

        co_a = make_company(db_session, name_norm="global tenant a")
        org_a = make_org(db_session, slug="global-org-a", company_id=co_a)

        # RLS on, authenticated as Tenant A
        _enable_rls(db_session)
        _set_org(db_session, org_a)

        row = db_session.execute(
            text("SELECT id FROM companies WHERE id = :id"),
            {"id": co},
        ).fetchone()
        assert row is not None, \
            "companies must be readable cross-tenant — it is global reference data"


# ---------------------------------------------------------------------------
# 7. UNIQUE (org_id, event_id, company_id) on risk_assessments is idempotent
# ---------------------------------------------------------------------------

class TestRiskAssessmentUniqueConstraint:
    def test_recompute_upserts_not_duplicates(self, db_session):
        """
        Inserting the same (org_id, event_id, company_id) triple a second time
        should raise IntegrityError, proving the constraint exists. The application
        layer uses ON CONFLICT DO UPDATE to handle this idempotently; here we just
        confirm the constraint fires.
        """
        co = make_company(db_session, name_norm="unique ra co")
        org = make_org(db_session, slug="unique-ra-org", company_id=co)

        ev_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO events (id, event_cluster_key, event_type, summary, created_at, updated_at)
                VALUES (:id, 'uniq-cluster', 'tariff_change', 'Tariff test', NOW(), NOW())
                """
            ),
            {"id": ev_id},
        )

        def _insert_ra():
            db_session.execute(
                text(
                    """
                    INSERT INTO risk_assessments
                        (id, org_id, event_id, company_id, impact_score, severity_band,
                         confidence, factors, graph_path, model_version, created_at, updated_at)
                    VALUES
                        (gen_random_uuid(), :oid, :eid, :cid, 45.0, 'MEDIUM',
                         0.75, '{}'::jsonb, '[]'::jsonb, 'v1', NOW(), NOW())
                    """
                ),
                {"oid": org, "eid": ev_id, "cid": co},
            )

        _insert_ra()
        db_session.flush()

        with pytest.raises(IntegrityError):
            _insert_ra()
            db_session.flush()


# ---------------------------------------------------------------------------
# 8. alert_must_have_evidence trigger fires on bare INSERT
# ---------------------------------------------------------------------------

class TestAlertMustHaveEvidenceTrigger:
    def test_alert_without_evidence_raises(self, db_session):
        """
        Committing an alert with no alert_evidence rows must raise an exception
        (the deferred constraint trigger fires at COMMIT / FLUSH).
        """
        co = make_company(db_session, name_norm="evidence trigger co")
        org = make_org(db_session, slug="evidence-trigger-org", company_id=co)

        ev_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO events (id, event_cluster_key, event_type, summary, created_at, updated_at)
                VALUES (:id, 'trigger-cluster', 'export_prohibition', 'Trigger test', NOW(), NOW())
                """
            ),
            {"id": ev_id},
        )
        ra_id = uuid.uuid4()
        db_session.execute(
            text(
                """
                INSERT INTO risk_assessments
                    (id, org_id, event_id, company_id, impact_score, severity_band,
                     confidence, factors, graph_path, model_version, created_at, updated_at)
                VALUES (:id, :oid, :eid, :cid, 90.0, 'CRITICAL', 0.95,
                        '{}'::jsonb, '[]'::jsonb, 'v1', NOW(), NOW())
                """
            ),
            {"id": ra_id, "oid": org, "eid": ev_id, "cid": co},
        )

        # Insert an alert with NO corresponding alert_evidence
        db_session.execute(
            text(
                """
                INSERT INTO alerts
                    (id, org_id, risk_assessment_id, event_id, company_id,
                     headline, severity_band, impact_score, confidence,
                     created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :oid, :raid, :eid, :cid,
                     'Bare alert — no evidence', 'CRITICAL', 90.0, 0.95,
                     NOW(), NOW())
                """
            ),
            {"oid": org, "raid": ra_id, "eid": ev_id, "cid": co},
        )

        # The deferred trigger fires on flush/commit
        with pytest.raises(Exception, match="no evidence rows"):
            db_session.flush()


# ---------------------------------------------------------------------------
# 9. Trigram index is used for fuzzy name search on companies
# ---------------------------------------------------------------------------

class TestTrigramIndex:
    def test_trigram_similarity_finds_fuzzy_match(self, db_session):
        """
        Insert a company and confirm pg_trgm similarity() returns a non-zero
        score for a close variant of the name.
        """
        make_company(db_session, name_norm="semiconductor global corp", country="TW")
        db_session.flush()

        row = db_session.execute(
            text(
                """
                SELECT similarity(name_norm, 'semiconductor global') AS score
                FROM companies
                WHERE name_norm % 'semiconductor global'
                ORDER BY score DESC
                LIMIT 1
                """
            )
        ).fetchone()

        assert row is not None, "Trigram similarity search returned no results"
        assert row[0] > 0.3, f"Expected similarity > 0.3, got {row[0]}"

    def test_exact_norm_match(self, db_session):
        make_company(db_session, name_norm="exact match industries", country="US")
        db_session.flush()

        row = db_session.execute(
            text(
                "SELECT id FROM companies WHERE name_norm = 'exact match industries'"
            )
        ).fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# 10. Migration up/down: check_db_connection works against test schema
# ---------------------------------------------------------------------------

class TestSchemaIntegrity:
    def test_all_expected_tables_exist(self, db_session):
        expected = {
            "organizations", "organization_members",
            "companies", "company_identifiers", "company_aliases",
            "entity_resolution_reviews",
            "supplier_relationships", "locations", "company_locations",
            "data_sources", "source_records", "source_record_versions",
            "dead_letter_queue",
            "events", "event_source_records", "event_entities",
            "risk_model_versions", "risk_assessments",
            "alerts", "alert_evidence", "alert_actions",
            "uploaded_documents", "contracts", "purchase_orders",
            "spend_records", "spend_leakage_findings",
            "documents", "document_chunks", "embeddings", "agent_runs",
            "notification_preferences", "notifications", "notification_deliveries",
            "audit_logs",
        }
        rows = db_session.execute(
            text(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
        ).fetchall()
        existing = {r[0] for r in rows}
        missing = expected - existing
        assert not missing, f"Missing tables: {missing}"

    def test_rls_enabled_on_tenant_tables(self, db_session):
        rls_tables = {
            "supplier_relationships", "risk_assessments", "alerts",
            "uploaded_documents", "contracts", "purchase_orders",
            "spend_records", "spend_leakage_findings",
            "notification_preferences", "notifications",
        }
        rows = db_session.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND rowsecurity = true
                """
            )
        ).fetchall()
        rls_on = {r[0] for r in rows}
        missing_rls = rls_tables - rls_on
        assert not missing_rls, f"RLS not enabled on: {missing_rls}"

    def test_companies_has_no_rls(self, db_session):
        """companies must NOT have RLS — it is global reference data."""
        row = db_session.execute(
            text(
                "SELECT rowsecurity FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = 'companies'"
            )
        ).fetchone()
        assert row is not None
        assert row[0] is False, "companies must NOT have RLS"

    def test_audit_logs_no_update_delete_for_app_role(self, db_session):
        """
        The provenance_app role must not hold UPDATE or DELETE privileges on
        audit_logs — enforced by REVOKE in the migration.
        Skipped if the role doesn't exist (e.g. plain test DB without role setup).
        """
        row = db_session.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = 'provenance_app'")
        ).fetchone()
        if row is None:
            pytest.skip("provenance_app role not present in this test DB")

        priv_rows = db_session.execute(
            text(
                """
                SELECT privilege_type
                FROM information_schema.role_table_grants
                WHERE grantee = 'provenance_app'
                  AND table_name = 'audit_logs'
                """
            )
        ).fetchall()
        granted = {r[0] for r in priv_rows}
        assert "UPDATE" not in granted, "provenance_app must not have UPDATE on audit_logs"
        assert "DELETE" not in granted, "provenance_app must not have DELETE on audit_logs"
