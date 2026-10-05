"""
UK OFSI Sanctions List connector.
Architecture reference: §E.1 #8, §F.2, §F.3.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class UKOFSIConnector(SourceConnector):
    """
    UK HM Treasury / Office of Financial Sanctions Implementation (OFSI) connector.
    Downloads the consolidated sanctions list published on GOV.UK.
    """

    source_id: str = "uk_ofsi"
    source_type: str = "bulk_download"
    reliability: str = "high"

    DEFAULT_CSV_URL = (
        "https://assets.publishing.service.gov.uk/government/uploads/system/uploads/"
        "attachment_data/file/ConList.csv"
    )

    def __init__(self, download_url: str | None = None) -> None:
        self.download_url = download_url or self.DEFAULT_CSV_URL

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Downloads and parses UK OFSI consolidated CSV."""
        headers = {"User-Agent": "Provenance/1.0 (supply-chain-risk)"}
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(self.download_url, headers=headers)
            resp.raise_for_status()
            content = resp.text

        items = self.parse_csv(content)
        return FetchResult(
            items=items,
            next_cursor=None,
            metadata={"count": len(items)},
        )

    def parse_csv(self, csv_content: str) -> list[dict[str, Any]]:
        """Parses UK OFSI CSV into row dictionaries."""
        reader = csv.DictReader(io.StringIO(csv_content))
        items: list[dict[str, Any]] = []

        for row in reader:
            # Reconstruct full name from parts
            name_parts = [
                (row.get("Name 6") or "").strip(),
                (row.get("Name 1") or "").strip(),
                (row.get("Name 2") or "").strip(),
                (row.get("Name 3") or "").strip(),
                (row.get("Name 4") or "").strip(),
                (row.get("Name 5") or "").strip(),
            ]
            full_name = " ".join(p for p in name_parts if p).strip()

            group_id = (row.get("Group ID") or "").strip()
            group_type = (row.get("Group Type") or "Entity").strip()
            regime = (row.get("Regime") or "").strip()
            last_updated = (row.get("Last Updated") or "").strip()
            country = (row.get("Country") or "").strip()
            other_info = (row.get("Other Information") or "").strip()

            if full_name or group_id:
                items.append(
                    {
                        "group_id": group_id,
                        "name": full_name,
                        "group_type": group_type,
                        "regime": regime,
                        "last_updated": last_updated,
                        "country": country,
                        "other_information": other_info,
                    }
                )

        return items

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over UK OFSI group identity."""
        identity = {
            "group_id": raw.get("group_id"),
            "name": (raw.get("name") or "").strip().lower(),
            "regime": raw.get("regime"),
            "last_updated": raw.get("last_updated"),
            "country": raw.get("country"),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw UK OFSI entry."""
        group_id = str(raw.get("group_id", "")).strip()
        name = raw.get("name", "").strip()

        pub_date = None
        updated_str = raw.get("last_updated")
        if updated_str:
            # Handle DD/MM/YYYY or YYYY-MM-DD
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    pub_date = datetime.strptime(updated_str.strip(), fmt).date()
                    break
                except Exception:
                    pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=f"uk-{group_id}" if group_id else f"uk-{chash[:16]}",
            content_hash=chash,
            canonical_url="https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets",
            title=f"UK OFSI Sanctions [{raw.get('regime', 'Sanctions')}]: {name} ({raw.get('group_type', 'Entity')})",
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "group_id": group_id,
                "name": name,
                "group_type": raw.get("group_type"),
                "regime": raw.get("regime"),
                "country": raw.get("country"),
                "other_information": raw.get("other_information"),
                "jurisdiction": "GB",
            },
        )
