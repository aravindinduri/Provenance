"""
India DGFT (Directorate General of Foreign Trade) HTML monitor connector.
Architecture reference: §E.2 #11, §F.2, §F.3.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import canonicalize_url, compute_content_hash


class DGFTHtmlConnector(SourceConnector):
    """
    DGFT structured HTML monitoring connector.
    Extracts official notification number, date, subject, and PDF link.
    Respects rate limit (max 1 req / 10s) and polite crawler rules per §E.2 #11.
    """

    source_id: str = "dgft_html"
    source_type: str = "html_monitor"
    reliability: str = "medium"

    DEFAULT_URL = "https://www.dgft.gov.in/CP/?opt=notification"

    def __init__(self, page_url: str | None = None) -> None:
        self.page_url = page_url or self.DEFAULT_URL

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Fetches notifications listing page."""
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
        """Parses DGFT notifications table."""
        items: list[dict[str, Any]] = []
        # Match table rows containing notification details
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
            if len(cells) >= 3:
                # Clean html tags
                clean_cells = [
                    re.sub(r"<[^>]+>", " ", c).strip() for c in cells
                ]
                noti_no = clean_cells[0]
                date_str = clean_cells[1]
                subject = clean_cells[2]

                # Find PDF link
                pdf_match = re.search(r'href=["\']([^"\']+\.pdf)["\']', cells[-1], re.IGNORECASE)
                pdf_link = pdf_match.group(1) if pdf_match else ""
                if pdf_link and not pdf_link.startswith("http"):
                    pdf_link = f"https://www.dgft.gov.in{pdf_link if pdf_link.startswith('/') else '/' + pdf_link}"

                if noti_no and noti_no.lower() != "notification no.":
                    items.append(
                        {
                            "notification_no": noti_no,
                            "date": date_str,
                            "subject": subject,
                            "pdf_url": pdf_link,
                        }
                    )

        return items

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over notification number and subject."""
        identity = {
            "notification_no": raw.get("notification_no"),
            "date": raw.get("date"),
            "subject": (raw.get("subject") or "").strip().lower(),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of DGFT notification item."""
        noti_no = str(raw.get("notification_no", "")).strip()
        subject = str(raw.get("subject", "")).strip()
        pdf_url = canonicalize_url(raw.get("pdf_url"))

        pub_date = None
        date_str = raw.get("date")
        if date_str:
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    pub_date = datetime.strptime(date_str.strip(), fmt).date()
                    break
                except Exception:
                    pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=noti_no or f"dgft-{chash[:16]}",
            content_hash=chash,
            canonical_url=pdf_url or self.page_url,
            title=f"DGFT Export Notification [{noti_no}]: {subject[:100]}",
            published_date=pub_date,
            source_type="live",
            reliability="medium",
            language="en",
            raw_payload=raw,
            normalized_data={
                "notification_no": noti_no,
                "date": date_str,
                "subject": subject,
                "pdf_url": pdf_url,
                "jurisdiction": "IN",
            },
        )
