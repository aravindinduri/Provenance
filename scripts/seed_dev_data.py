#!/usr/bin/env python3
"""
seed_dev_data.py — Populate the local dev database with two realistic tenants,
a canonical company graph, and supplier relationships.

Usage (from repo root, with the venv active and postgres running):
    python scripts/seed_dev_data.py

Idempotent: safe to re-run — uses INSERT ... ON CONFLICT DO NOTHING for most
rows and checks for existence before creating graph edges.

What gets created
-----------------
Companies (global registry):
  - Acme Manufacturing Ltd          (Tenant A's own company)
  - Henan Yixin Specialty Alloys    (Tier-1 supplier — CN)
  - Jiangxi Rare Earth Co.          (Tier-2 sub-supplier — CN)
  - China Minmetals Corp            (Parent of Jiangxi RE — CN)
  - Becker Precision GmbH           (Tier-1 supplier — DE)
  - Becker Group AG                 (Parent of Becker Precision — DE)
  - Novex Electronics Pvt Ltd       (Tier-1 supplier — IN)

  - Greenfield Components Inc       (Tenant B's own company)
  - Coastal Polymers Ltd            (Tier-1 supplier — IN)
  - PolySource GmbH                 (Tier-1 supplier — DE)

Tenants (organizations):
  - Acme Manufacturing              (slug: acme-manufacturing)
  - Greenfield Procurement          (slug: greenfield-procurement)

Members:
  - Alice (risk_manager, analyst) in Acme
  - Bob   (category_manager, analyst) in Acme
  - Carol (risk_manager, analyst) in Greenfield

Relationships (Acme's graph):
  Henan Yixin   --supplies_to-->      Acme (tier 1, criticality 5, CN, single_source)
  Jiangxi RE    --sub_supplies_to-->  Henan Yixin (tier 2)
  China Minmetals--owned_by-->        Jiangxi RE (parent)
  Becker GmbH   --supplies_to-->      Acme (tier 1, criticality 3, DE)
  Becker Group  --owned_by-->         Becker GmbH (parent, GLEIF-seeded)
  Novex Elec    --supplies_to-->      Acme (tier 1, criticality 2, IN)

Relationships (Greenfield's graph — entirely separate, no leakage):
  Coastal Polymers--supplies_to-->    Greenfield (tier 1, criticality 4, IN)
  PolySource GmbH --supplies_to-->    Greenfield (tier 1, criticality 2, DE)
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timezone

# ── Make backend importable from the repo root ────────────────────────────────
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend   = os.path.join(_repo_root, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import re

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings


# ── DB connection (sync, for a one-shot script) ───────────────────────────────
def _sync_url() -> str:
    url = get_settings().database_url
    return re.sub(r"^postgresql\+asyncpg", "postgresql+psycopg2", url)


engine = create_engine(_sync_url(), echo=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert_company(
    session: Session,
    *,
    legal_name: str,
    name_norm: str,
    country: str,
    data_source: str = "user",
    enrichment_status: str = "pending",
    is_verified: bool = False,
    lei: str | None = None,
    industry_codes: list[str] | None = None,
) -> uuid.UUID:
    """Insert a company if the normalised name + country doesn't exist yet."""
    row = session.execute(
        text(
            "SELECT id FROM companies "
            "WHERE name_norm = :n AND country = :c AND deleted_at IS NULL"
        ),
        {"n": name_norm, "c": country},
    ).fetchone()
    if row:
        company_id = row[0]
    else:
        company_id = uuid.uuid4()
        session.execute(
            text(
                """
                INSERT INTO companies
                    (id, legal_name, name_norm, country, data_source,
                     enrichment_status, is_verified,
                     industry_codes, created_at, updated_at)
                VALUES
                    (:id, :legal_name, :name_norm, :country, :data_source,
                     :enrichment_status, :is_verified,
                     :industry_codes, NOW(), NOW())
                """
            ),
            {
                "id": company_id,
                "legal_name": legal_name,
                "name_norm": name_norm,
                "country": country,
                "data_source": data_source,
                "enrichment_status": enrichment_status,
                "is_verified": is_verified,
                "industry_codes": industry_codes or [],
            },
        )
    # Optionally attach a LEI identifier
    if lei:
        session.execute(
            text(
                """
                INSERT INTO company_identifiers
                    (id, company_id, identifier_type, identifier_value,
                     issuing_country, source, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :cid, 'lei', :lei, :country, 'gleif', NOW(), NOW())
                ON CONFLICT (identifier_type, identifier_value) DO NOTHING
                """
            ),
            {"cid": company_id, "lei": lei, "country": country},
        )
    return company_id


def _upsert_org(
    session: Session,
    *,
    clerk_org_id: str,
    name: str,
    slug: str,
    company_id: uuid.UUID,
    country: str = "IN",
) -> uuid.UUID:
    row = session.execute(
        text("SELECT id FROM organizations WHERE clerk_org_id = :c"),
        {"c": clerk_org_id},
    ).fetchone()
    if row:
        return row[0]
    org_id = uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO organizations
                (id, clerk_org_id, name, slug, company_id, country,
                 subscription_tier, settings, monthly_token_budget,
                 onboarding_completed_at, created_at, updated_at)
            VALUES
                (:id, :clerk_org_id, :name, :slug, :company_id, :country,
                 'free', '{}'::jsonb, 5000000, NOW(), NOW(), NOW())
            """
        ),
        {
            "id": org_id,
            "clerk_org_id": clerk_org_id,
            "name": name,
            "slug": slug,
            "company_id": company_id,
            "country": country,
        },
    )
    return org_id


def _upsert_member(
    session: Session,
    *,
    org_id: uuid.UUID,
    user_id: str,
    role: str,
    persona: str,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO organization_members
                (id, org_id, user_id, role, persona, joined_at, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :org_id, :user_id, :role, :persona, NOW(), NOW(), NOW())
            ON CONFLICT (org_id, user_id) DO NOTHING
            """
        ),
        {"org_id": org_id, "user_id": user_id, "role": role, "persona": persona},
    )


def _upsert_edge(
    session: Session,
    *,
    org_id: uuid.UUID,
    from_company_id: uuid.UUID,
    to_company_id: uuid.UUID | None = None,
    to_org_id: uuid.UUID | None = None,
    relationship_type: str,
    tier: int | None = None,
    criticality: int | None = None,
    annual_spend_usd: float | None = None,
    category: str | None = None,
    single_source: bool = False,
    source: str = "user_declared",
    confidence: float = 1.0,
) -> None:
    """Insert a graph edge; skip silently if an identical active edge exists."""
    existing = session.execute(
        text(
            """
            SELECT id FROM supplier_relationships
            WHERE org_id = :org_id
              AND from_company_id = :from_cid
              AND (to_company_id = :to_cid OR (to_company_id IS NULL AND :to_cid IS NULL))
              AND relationship_type = :rtype
              AND valid_to IS NULL
            """
        ),
        {
            "org_id": org_id,
            "from_cid": from_company_id,
            "to_cid": to_company_id,
            "rtype": relationship_type,
        },
    ).fetchone()
    if existing:
        return
    session.execute(
        text(
            """
            INSERT INTO supplier_relationships
                (id, org_id, from_company_id, to_company_id, to_org_id,
                 relationship_type, tier, criticality, annual_spend_usd,
                 category, single_source, confidence, source,
                 valid_from, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :org_id, :from_cid, :to_cid, :to_oid,
                 :rtype, :tier, :criticality, :spend,
                 :category, :single_source, :confidence, :source,
                 CURRENT_DATE, NOW(), NOW())
            """
        ),
        {
            "org_id": org_id,
            "from_cid": from_company_id,
            "to_cid": to_company_id,
            "to_oid": to_org_id,
            "rtype": relationship_type,
            "tier": tier,
            "criticality": criticality,
            "spend": annual_spend_usd,
            "category": category,
            "single_source": single_source,
            "confidence": confidence,
            "source": source,
        },
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # RLS requires app.current_org_id to be set for tenant-scoped writes.
    # We use a superuser connection in dev so we bypass RLS entirely here
    # by setting it to a sentinel that won't match any policy.
    # In production the app sets this via TenantContextMiddleware.
    with Session(engine) as session:
        # Disable RLS for this seed session (superuser bypasses it, but be explicit)
        session.execute(text("SET LOCAL row_security = off;"))

        print("── Creating global company registry entries ──────────────────")

        # ── Tenant A companies ────────────────────────────────────────────
        acme_id = _upsert_company(
            session,
            legal_name="Acme Manufacturing Ltd",
            name_norm="acme manufacturing",
            country="IN",
            data_source="user",
            is_verified=True,
            industry_codes=["C28", "C29"],
        )
        print(f"  Acme Manufacturing Ltd          id={acme_id}")

        yixin_id = _upsert_company(
            session,
            legal_name="Henan Yixin Specialty Alloys Co., Ltd",
            name_norm="henan yixin specialty alloys",
            country="CN",
            data_source="gleif",
            enrichment_status="enriched",
            industry_codes=["C24"],
        )
        print(f"  Henan Yixin Specialty Alloys    id={yixin_id}")

        jiangxi_id = _upsert_company(
            session,
            legal_name="Jiangxi Rare Earth Co., Ltd",
            name_norm="jiangxi rare earth",
            country="CN",
            data_source="gleif",
            enrichment_status="enriched",
            industry_codes=["B07"],
        )
        print(f"  Jiangxi Rare Earth Co.          id={jiangxi_id}")

        minmetals_id = _upsert_company(
            session,
            legal_name="China Minmetals Corporation",
            name_norm="china minmetals",
            country="CN",
            data_source="gleif",
            enrichment_status="enriched",
            industry_codes=["G46"],
        )
        print(f"  China Minmetals Corp            id={minmetals_id}")

        becker_id = _upsert_company(
            session,
            legal_name="Becker Precision GmbH",
            name_norm="becker precision",
            country="DE",
            data_source="gleif",
            enrichment_status="enriched",
            industry_codes=["C28"],
        )
        print(f"  Becker Precision GmbH           id={becker_id}")

        becker_group_id = _upsert_company(
            session,
            legal_name="Becker Group AG",
            name_norm="becker group",
            country="DE",
            data_source="gleif",
            enrichment_status="enriched",
            confidence=0.95,
            industry_codes=["M70"],
        )
        print(f"  Becker Group AG                 id={becker_group_id}")

        novex_id = _upsert_company(
            session,
            legal_name="Novex Electronics Pvt Ltd",
            name_norm="novex electronics",
            country="IN",
            data_source="user",
            industry_codes=["C26"],
        )
        print(f"  Novex Electronics Pvt Ltd       id={novex_id}")

        # ── Tenant B companies ────────────────────────────────────────────
        greenfield_id = _upsert_company(
            session,
            legal_name="Greenfield Components Inc",
            name_norm="greenfield components",
            country="US",
            data_source="user",
            is_verified=True,
            industry_codes=["C25"],
        )
        print(f"  Greenfield Components Inc       id={greenfield_id}")

        coastal_id = _upsert_company(
            session,
            legal_name="Coastal Polymers Ltd",
            name_norm="coastal polymers",
            country="IN",
            data_source="user",
            industry_codes=["C22"],
        )
        print(f"  Coastal Polymers Ltd            id={coastal_id}")

        polysource_id = _upsert_company(
            session,
            legal_name="PolySource GmbH",
            name_norm="polysource",
            country="DE",
            data_source="gleif",
            industry_codes=["C22"],
        )
        print(f"  PolySource GmbH                 id={polysource_id}")

        session.flush()

        # ── Organizations ─────────────────────────────────────────────────
        print("\n── Creating organizations ────────────────────────────────────")

        acme_org_id = _upsert_org(
            session,
            clerk_org_id="org_dev_acme_001",
            name="Acme Manufacturing",
            slug="acme-manufacturing",
            company_id=acme_id,
            country="IN",
        )
        print(f"  Acme Manufacturing              org_id={acme_org_id}")

        greenfield_org_id = _upsert_org(
            session,
            clerk_org_id="org_dev_greenfield_001",
            name="Greenfield Procurement",
            slug="greenfield-procurement",
            company_id=greenfield_id,
            country="US",
        )
        print(f"  Greenfield Procurement          org_id={greenfield_org_id}")

        session.flush()

        # ── Members ───────────────────────────────────────────────────────
        print("\n── Creating members ──────────────────────────────────────────")

        _upsert_member(
            session,
            org_id=acme_org_id,
            user_id="user_dev_alice",
            role="analyst",
            persona="risk_manager",
        )
        print("  Alice (risk_manager/analyst)    → Acme Manufacturing")

        _upsert_member(
            session,
            org_id=acme_org_id,
            user_id="user_dev_bob",
            role="analyst",
            persona="category_manager",
        )
        print("  Bob   (category_manager/analyst)→ Acme Manufacturing")

        _upsert_member(
            session,
            org_id=greenfield_org_id,
            user_id="user_dev_carol",
            role="analyst",
            persona="risk_manager",
        )
        print("  Carol (risk_manager/analyst)    → Greenfield Procurement")

        session.flush()

        # ── Acme supplier graph ───────────────────────────────────────────
        print("\n── Building Acme's supply graph ──────────────────────────────")

        # Tier-1: Henan Yixin → Acme (rare-earth alloys, single source, critical)
        _upsert_edge(
            session,
            org_id=acme_org_id,
            from_company_id=yixin_id,
            to_org_id=acme_org_id,
            relationship_type="supplies_to",
            tier=1,
            criticality=5,
            annual_spend_usd=4_200_000.00,
            category="rare_earth_alloys",
            single_source=True,
        )
        print("  Henan Yixin    --supplies_to-->  Acme  (tier=1 crit=5 single_source)")

        # Tier-2: Jiangxi RE sub-supplies to Henan Yixin
        _upsert_edge(
            session,
            org_id=acme_org_id,
            from_company_id=jiangxi_id,
            to_company_id=yixin_id,
            relationship_type="sub_supplies_to",
            tier=2,
            criticality=4,
            category="rare_earth_mining",
            confidence=0.90,
            source="inferred",
        )
        print("  Jiangxi RE     --sub_supplies_to--> Henan Yixin  (tier=2 inferred)")

        # Parent edge: China Minmetals owns Jiangxi RE (GLEIF Level 2)
        _upsert_edge(
            session,
            org_id=acme_org_id,
            from_company_id=jiangxi_id,
            to_company_id=minmetals_id,
            relationship_type="owned_by",
            confidence=0.98,
            source="gleif",
        )
        print("  Jiangxi RE     --owned_by-->      China Minmetals  (gleif)")

        # Tier-1: Becker Precision → Acme (precision machined parts)
        _upsert_edge(
            session,
            org_id=acme_org_id,
            from_company_id=becker_id,
            to_org_id=acme_org_id,
            relationship_type="supplies_to",
            tier=1,
            criticality=3,
            annual_spend_usd=1_850_000.00,
            category="precision_machined_parts",
        )
        print("  Becker GmbH    --supplies_to-->  Acme  (tier=1 crit=3)")

        # Parent edge: Becker Group owns Becker Precision (GLEIF Level 2)
        _upsert_edge(
            session,
            org_id=acme_org_id,
            from_company_id=becker_id,
            to_company_id=becker_group_id,
            relationship_type="owned_by",
            confidence=0.95,
            source="gleif",
        )
        print("  Becker GmbH    --owned_by-->      Becker Group AG  (gleif)")

        # Tier-1: Novex Electronics → Acme (PCB assemblies)
        _upsert_edge(
            session,
            org_id=acme_org_id,
            from_company_id=novex_id,
            to_org_id=acme_org_id,
            relationship_type="supplies_to",
            tier=1,
            criticality=2,
            annual_spend_usd=720_000.00,
            category="pcb_assemblies",
        )
        print("  Novex Elec     --supplies_to-->  Acme  (tier=1 crit=2)")

        # ── Greenfield supplier graph (completely separate) ────────────────
        print("\n── Building Greenfield's supply graph ────────────────────────")

        _upsert_edge(
            session,
            org_id=greenfield_org_id,
            from_company_id=coastal_id,
            to_org_id=greenfield_org_id,
            relationship_type="supplies_to",
            tier=1,
            criticality=4,
            annual_spend_usd=2_100_000.00,
            category="polymer_resins",
        )
        print("  Coastal Polymers--supplies_to--> Greenfield  (tier=1 crit=4)")

        _upsert_edge(
            session,
            org_id=greenfield_org_id,
            from_company_id=polysource_id,
            to_org_id=greenfield_org_id,
            relationship_type="supplies_to",
            tier=1,
            criticality=2,
            annual_spend_usd=900_000.00,
            category="polymer_resins",
        )
        print("  PolySource GmbH --supplies_to--> Greenfield  (tier=1 crit=2)")

        session.commit()

    print("\n✓ Dev data seeded successfully.")
    print(f"  Tenant A: Acme Manufacturing      org_id={acme_org_id}")
    print(f"  Tenant B: Greenfield Procurement  org_id={greenfield_org_id}")
    print(
        "\n  Henan Yixin and Jiangxi RE are visible ONLY in Acme's graph."
        "\n  Coastal Polymers and PolySource are visible ONLY in Greenfield's graph."
        "\n  Verify with: SELECT count(*) FROM supplier_relationships WHERE org_id = '<acme>';"
    )


if __name__ == "__main__":
    main()
