"""
India CBIC (Central Board of Indirect Taxes & Customs) HTML monitor connector.
Architecture reference: §E.2 #11, §F.2, §F.3.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import canonicalize_url, compute_content_hash


class CBICHtmlConnector(SourceConnector):
    """
    CBIC customs tariff notification HTML monitor.
    Extracts customs notifications altering tariff rates or import/export procedures.
    """

    source_id: str = "cbic_html"
    source_type: str = "html_monitor"
    reliability: str = "medium"

    DEFAULT_URL = "https://www.cbic.gov.in/htdocs-cbec/customs/cs-act/notifications/notifs-2026"

    def __init__(self, page_url: str | None = None) -> None:
        self.page_url = page_url or self.DEFAULT_URL

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Fetches CBIC customs notification page."""
        headers = {
            "User-Agent": "Provenance/1.0 (supply-chain-risk-polite-crawler)",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.page_url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        items = self.parse_html(html)
        return FetchResult(items=items, next_cursor=None, metadata={"count": len(items)})

    def parse_html(self, html: str) -> list[dict[str, Any]]:
        """Parses CBIC items."""
        items: list[dict[str, Any]] = []
        # Find item containers
        blocks = re.findall(r'<div[^>]*class=["\'][^"\']*item[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
        for block in blocks:
            num_match = re.search(r'class=["\'][^"\']*noti-num[^"\']*["\'][^>]*>(.*?)</span>', block, re.DOTALL | re.IGNORECASE)
            date_match = re.search(r'class=["\'][^"\']*noti-date[^"\']*["\'][^>]*>(.*?)</span>', block, re.DOTALL | re.IGNORECASE)
            desc_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL | re.IGNORECASE)
            pdf_match = re.search(r'href=["\']([^"\']+\.pdf)["\']', block, re.IGNORECASE)

            if num_match:
                items.append(
                    {
                        "notification_number": re.sub(r"<[^>]+>", "", num_match.group(1)).strip(),
                        "date": re.sub(r"<[^>]+>", "", date_match.group(1)).strip() if date_match else "",
                        "description": re.sub(r"<[^>]+>", "", desc_match.group(1)).strip() if desc_match else "",
                        "pdf_url": pdf_match.group(1) if pdf_match else "",
                    }
                )

        return items

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over notification number and date."""
        identity = {
            "notification_number": raw.get("notification_number"),
            "date": raw.get("date"),
            "description": (raw.get("description") or "").strip().lower(),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of CBIC customs notification."""
        noti_num = str(raw.get("notification_number", "")).strip()
        desc = str(raw.get("description", "")).strip()
        pdf_url = canonicalize_url(raw.get("pdf_url"))

        pub_date = None
        date_str = raw.get("date")
        if date_str:
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    pub_date = datetime.strptime(date_str.strip(), fmt).date()
                    break
                except Exception:
                    pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=noti_num or f"cbic-{chash[:16]}",
            content_hash=chash,
            canonical_url=pdf_url or self.page_url,
            title=f"CBIC Customs Tariff Notice: {noti_num}",
            published_date=pub_date,
            source_type="live",
            reliability="medium",
            language="en",
            raw_payload=raw,
            normalized_data={
                "notification_number": noti_num,
                "date": date_str,
                "description": desc,
                "pdf_url": pdf_url,
                "jurisdiction": "IN",
            },
        )
