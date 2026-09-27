"""
Shared pytest fixtures for Phase 2 tests.

Requires a running Postgres with pgvector + pg_trgm extensions.
Set DATABASE_URL env var (or .env) to point at a test database —
the fixtures create/drop all tables around each test session.
"""

from __future__ import annotations

import os
import re
import uuid

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session


def _sync_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://provenance:provenance@localhost:5432/provenance_test",
    )
    return re.sub(r"^postgresql\+asyncpg", "postgresql+psycopg2", url)


@pytest.fixture(scope="session")
def db_engine():
    """Create schema once for the whole test session."""
    engine = create_engine(_sync_url(), echo=False)

    # Extensions must exist (created by init.sql in docker or manually)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        conn.commit()

    # Import models so metadata is populated, then run the migration
    import app.db.models  # noqa: F401
    from app.db.base import Base

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """
    Per-test session wrapped in a SAVEPOINT that is always rolled back.
    RLS session variable is set to a sentinel UUID so policies don't interfere
    with the isolation tests (which set it explicitly themselves).
    """
    conn = db_engine.connect()
    trans = conn.begin()
    session = Session(bind=conn)

    # Disable RLS by default so fixture setup can insert cross-tenant data
    session.execute(text("SET LOCAL row_security = off;"))

    yield session

    session.close()
    trans.rollback()
    conn.close()


# ── Minimal factories ─────────────────────────────────────────────────────────

def make_company(session: Session, *, name_norm: str, country: str = "US") -> uuid.UUID:
    cid = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO companies (id, legal_name, name_norm, country, created_at, updated_at)
            VALUES (:id, :ln, :nn, :c, NOW(), NOW())
            """
        ),
        {"id": cid, "ln": name_norm.title(), "nn": name_norm, "c": country},
    )
    return cid


def make_org(session: Session, *, slug: str, company_id: uuid.UUID) -> uuid.UUID:
    oid = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO organizations
                (id, clerk_org_id, name, slug, company_id, created_at, updated_at)
            VALUES
                (:id, :cok, :name, :slug, :cid, NOW(), NOW())
            """
        ),
        {
            "id": oid,
            "cok": f"clerk_{slug}",
            "name": slug.replace("-", " ").title(),
            "slug": slug,
            "cid": company_id,
        },
    )
    return oid


def make_edge(
    session: Session,
    *,
    org_id: uuid.UUID,
    from_company_id: uuid.UUID,
    to_org_id: uuid.UUID,
) -> uuid.UUID:
    eid = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO supplier_relationships
                (id, org_id, from_company_id, to_org_id,
                 relationship_type, confidence, source, valid_from,
                 created_at, updated_at)
            VALUES
                (:id, :oid, :fcid, :toid,
                 'supplies_to', 1.0, 'user_declared', CURRENT_DATE,
                 NOW(), NOW())
            """
        ),
        {"id": eid, "oid": org_id, "fcid": from_company_id, "toid": to_org_id},
    )
    return eid
