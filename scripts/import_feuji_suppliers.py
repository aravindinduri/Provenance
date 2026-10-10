#!/usr/bin/env python3
"""
scripts/import_feuji_suppliers.py — Ingest authentic real technology vendors & partners for Feuji Inc.
Imports 100% real companies across the United States and India.
Usage:
    python scripts/import_feuji_suppliers.py
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Setup paths
_repo_root = Path(__file__).resolve().parent.parent
_backend = _repo_root / "backend"
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_backend))

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.modules.graph.bulk_service import bulk_job_store, execute_bulk_supplier_job, parse_supplier_csv


async def main() -> None:
    settings = get_settings()
    csv_path = _repo_root / "feuji_real_suppliers.csv"

    if not csv_path.exists():
        print(f"[!] Error: {csv_path} not found.")
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_text = f.read()

    rows, errors = parse_supplier_csv(csv_text)
    if errors:
        print(f"[!] Warning: Found {len(errors)} CSV parse errors:")
        for err in errors:
            print(f"    Row {err.row}: {err.error}")

    print(f"[*] Parsed {len(rows)} real companies from feuji_real_suppliers.csv:")
    for r in rows:
        print(f"    - {r.legal_name:<38} [{r.country}]  Tier-{r.tier} (Crit: {r.criticality}) Domain: {r.primary_domain}")

    # Resolve Feuji Inc. org_id
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        org_row = await session.execute(
            text("SELECT id, name FROM organizations WHERE slug = 'feuji-inc' OR name ILIKE '%feuji%' LIMIT 1")
        )
        rec = org_row.fetchone()
        if not rec:
            print("[!] Feuji Inc. organization not found. Please ensure seed_dev_data.py has run.")
            sys.exit(1)

        org_id = rec[0]
        print(f"\n[*] Target Organization: {rec[1]} (ID: {org_id})")

    # Create job in job store
    job = bulk_job_store.create_job(org_id=org_id, total_rows=len(rows))
    print(f"[*] Ingesting {len(rows)} real vendors via entity resolution pipeline (Job: {job.job_id})...")

    await execute_bulk_supplier_job(
        job_id=job.job_id,
        org_id=org_id,
        rows=rows,
        parse_errors=errors,
    )

    final_job = bulk_job_store.get_job(job.job_id, org_id)
    if final_job:
        print(f"\n[OK] Import Complete!")
        print(f"    Total Processed: {final_job.processed_rows}")
        print(f"    Successful:      {final_job.successful_rows}")
        print(f"    Failed:          {final_job.failed_rows}")

    async with session_factory() as session:
        cnt = (await session.execute(
            text("SELECT count(*) FROM supplier_relationships WHERE org_id = :oid AND deleted_at IS NULL"),
            {"oid": org_id},
        )).scalar()
        comp_cnt = (await session.execute(text("SELECT count(*) FROM companies WHERE deleted_at IS NULL"))).scalar()
        print(f"\n[OK] Active Live Graph Nodes: {cnt} suppliers linked, {comp_cnt} registered global companies.")


if __name__ == "__main__":
    asyncio.run(main())
