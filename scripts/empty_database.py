#!/usr/bin/env python3
"""
scripts/empty_database.py — Completely wipe all user, tenant, company, graph, and transactional data.
Keeps migrations (alembic_version) and static connector configurations (data_sources).
Prepares the database for a clean user registration and fresh onboarding.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Setup paths
_repo_root = Path(__file__).resolve().parent.parent
_backend = _repo_root / "backend"
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_backend))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from app.config import get_settings


def _sync_url() -> str:
    url = get_settings().database_url
    return re.sub(r"^postgresql\+asyncpg", "postgresql+psycopg2", url)


def empty_database() -> None:
    settings = get_settings()
    engine = create_engine(_sync_url(), echo=False)

    print("=" * 70)
    print("PROVENANCE DATABASE CLEANUP")
    print("Emptying all users, companies, organizations, and graph data...")
    print("=" * 70)

    # Tables to completely truncate/delete in foreign-key dependency order
    tables_to_wipe = [
        # AI / RAG
        "embeddings",
        "document_chunks",
        "documents",
        "agent_runs",
        # Notifications
        "notification_deliveries",
        "notifications",
        "notification_preferences",
        # Alerts & Actions
        "alert_evidence",
        "alert_actions",
        "alerts",
        # Risk
        "risk_assessments",
        "risk_model_versions",
        # Spend
        "spend_leakage_findings",
        "spend_records",
        "purchase_orders",
        "contracts",
        "uploaded_documents",
        # Graph & Companies
        "supplier_relationships",
        "entity_resolution_reviews",
        "company_locations",
        "locations",
        "company_identifiers",
        "company_aliases",
        "event_entities",
        "event_source_records",
        "events",
        "source_record_versions",
        "source_records",
        "dead_letter_queue",
        # Audit
        "audit_logs",
        # Members & Users
        "organization_members",
        "users",
        # Tenancy & Companies
        "organizations",
        "companies",
    ]

    with Session(engine) as session:
        # Disable RLS and triggers for fast clean cascade
        session.execute(text("SET LOCAL row_security = off;"))

        # Unlink circular foreign key: organizations.company_id -> companies.id
        try:
            session.execute(text("UPDATE organizations SET company_id = NULL WHERE company_id IS NOT NULL;"))
            session.commit()
        except Exception as e:
            session.rollback()

        # Wipe tables
        for table in tables_to_wipe:
            try:
                # Use TRUNCATE CASCADE if supported, fallback to DELETE
                session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE;'))
                session.commit()
                print(f"  [OK] Truncated {table}")
            except Exception:
                session.rollback()
                try:
                    session.execute(text(f'DELETE FROM "{table}";'))
                    session.commit()
                    print(f"  [OK] Deleted all rows from {table}")
                except Exception as del_err:
                    session.rollback()
                    # Table might not exist yet if migrations haven't created it
                    print(f"  [-] Skipped {table} ({del_err})")

    # Verify counts
    print("\n" + "=" * 70)
    print("VERIFICATION AUDIT:")
    with Session(engine) as session:
        # Dynamically query all public tables
        all_tables_res = session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            )
        ).fetchall()
        all_empty = True
        for (tbl,) in all_tables_res:
            cnt = session.execute(text(f'SELECT count(*) FROM "{tbl}";')).scalar()
            if tbl in ("alembic_version", "data_sources"):
                print(f"  - {tbl:<28}: {cnt} rows (reference / metadata)")
            else:
                print(f"  - {tbl:<28}: {cnt} rows")
                if cnt != 0:
                    all_empty = False

        print("=" * 70)
        if all_empty:
            print("[SUCCESS] All user, tenant, graph, and entity tables are 100% EMPTY.")
            print("The system is clean and ready for new user registration and testing.")
        else:
            print("[WARNING] Some data tables still contain rows.")
    print("=" * 70)


if __name__ == "__main__":
    empty_database()
