"""
scripts/verify_sources.py — Verification script for Phase 8 data source connectors.
Tests live connectivity and normalization for all Tier-1 data sources.
Run:
    python scripts/verify_sources.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root and backend to python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from ingestion.connectors.registry import CONNECTOR_CLASSES, get_connector
from ingestion.connectors.rate_limiter import get_token_bucket_limiter

SOURCES_TO_VERIFY = [
    "ofac_sls",
    "gleif",
    "gdelt_doc",
    "federal_register",
    "eurlex",
    "eu_sanctions",
    "un_sanctions",
    "uk_ofsi",
    "data_gov_in",
]


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", "ascii") or "ascii"
        print(msg.encode(encoding, errors="replace").decode(encoding))


async def verify_source(source_key: str) -> dict[str, any]:
    safe_print(f"\n[+] Verifying connector: {source_key} ...")
    start_time = time.time()
    connector = get_connector(source_key)

    result = {
        "source_key": source_key,
        "type": connector.source_type,
        "reliability": connector.reliability,
        "live_fetch_success": False,
        "fixture_fallback_success": False,
        "items_count": 0,
        "normalized_sample": None,
        "error": None,
        "duration_seconds": 0.0,
    }

    try:
        # Attempt live fetch with a 12s timeout per source
        fetch_res = await asyncio.wait_for(connector.fetch(), timeout=12.0)
        result["live_fetch_success"] = True
        result["items_count"] = len(fetch_res.items)
        if fetch_res.items:
            norm = connector.normalize(fetch_res.items[0])
            result["normalized_sample"] = norm.title
            safe_print(f"    [OK] Live fetch succeeded: {len(fetch_res.items)} items.")
            safe_print(f"    [OK] Sample title: {norm.title}")
    except Exception as exc:
        result["error"] = str(exc)
        safe_print(f"    [WARN] Live fetch note ({exc}). Testing recorded fixture...")
        # Fallback to fixture verification to ensure parsing/normalization is sound
        fixture_paths = {
            "ofac_sls": ROOT / "ingestion" / "fixtures" / "ofac_sls.xml",
            "gleif": ROOT / "ingestion" / "fixtures" / "gleif.json",
            "gdelt_doc": ROOT / "ingestion" / "fixtures" / "gdelt.json",
            "federal_register": ROOT / "ingestion" / "fixtures" / "federal_register.json",
            "eurlex": ROOT / "ingestion" / "fixtures" / "eurlex.xml",
            "eu_sanctions": ROOT / "ingestion" / "fixtures" / "eu_sanctions.xml",
            "un_sanctions": ROOT / "ingestion" / "fixtures" / "un_sanctions.xml",
            "uk_ofsi": ROOT / "ingestion" / "fixtures" / "uk_ofsi.csv",
            "data_gov_in": ROOT / "ingestion" / "fixtures" / "data_gov_in.json",
        }
        fpath = fixture_paths.get(source_key)
        if fpath and fpath.exists():
            import json
            content = fpath.read_text(encoding="utf-8")
            if str(fpath).endswith(".json"):
                data = json.loads(content)
                items = data.get("articles") or data.get("data") or data.get("results") or data.get("records") or []
            elif str(fpath).endswith(".xml"):
                if hasattr(connector, "parse_xml_entries"):
                    items = connector.parse_xml_entries(content)
                elif hasattr(connector, "parse_xml"):
                    items = connector.parse_xml(content)
                elif hasattr(connector, "parse_feed"):
                    items = connector.parse_feed(content)
                else:
                    items = []
            elif str(fpath).endswith(".csv"):
                items = connector.parse_csv(content) if hasattr(connector, "parse_csv") else []
            else:
                items = []

            result["fixture_fallback_success"] = len(items) > 0
            result["items_count"] = len(items)
            if items:
                norm = connector.normalize(items[0])
                result["normalized_sample"] = norm.title
                safe_print(f"    [OK] Fixture verification passed: {len(items)} items normalized.")

    result["duration_seconds"] = round(time.time() - start_time, 2)
    return result


async def main():
    safe_print("=" * 70)
    safe_print(" PROVENANCE DATA SOURCES VERIFICATION (PHASE 8)")
    safe_print("=" * 70)

    results = []
    for s_key in SOURCES_TO_VERIFY:
        res = await verify_source(s_key)
        results.append(res)

    safe_print("\n" + "=" * 70)
    safe_print(" SUMMARY")
    safe_print("=" * 70)
    for r in results:
        status_str = "LIVE PASS" if r["live_fetch_success"] else ("FIXTURE PASS" if r["fixture_fallback_success"] else "FAIL")
        safe_print(f" - {r['source_key']:<20} [{status_str:<12}] {r['items_count']} items in {r['duration_seconds']}s")

    safe_print("\nVerification complete.")


if __name__ == "__main__":
    asyncio.run(main())
