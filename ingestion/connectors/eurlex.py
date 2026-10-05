"""
EUR-Lex / EU Official Journal connector.
Architecture reference: §E.1 #5, §F.2, §F.3.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import canonicalize_url, compute_content_hash


class EURLexConnector(SourceConnector):
    """
    EUR-Lex connector for EU regulations, decisions, and restrictive measures.
    Fetches official journal acts via RSS and SPARQL endpoints.
    """

    source_id: str = "eurlex"
    source_type: str = "api"
    reliability: str = "high"

    DEFAULT_RSS_URL = "https://eur-lex.europa.eu/RSSONE.do?ihmlang=en"

    def __init__(self, feed_url: str | None = None) -> None:
        self.feed_url = feed_url or self.DEFAULT_RSS_URL

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Fetches RSS feed or SPARQL results from EUR-Lex."""
        url = cursor or self.feed_url
        headers = {"Accept": "application/rss+xml, application/xml, text/xml, */*"}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            content = resp.text

        items = self.parse_feed(content)
        return FetchResult(
            items=items,
            next_cursor=None,
            metadata={"count": len(items)},
        )

    def parse_feed(self, xml_content: str) -> list[dict[str, Any]]:
        """Parses RSS/Atom XML from EUR-Lex."""
        root = ET.fromstring(xml_content)
        # Strip namespaces
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        items: list[dict[str, Any]] = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub_date = item.findtext("date", "").strip()
            guid = item.findtext("guid", "").strip() or link

            # Extract CELEX if available
            celex = ""
            if "celex:" in guid.lower():
                celex = guid.split(":", 1)[1]
            elif "celex=" in link.lower():
                parts = link.split("celex=")
                if len(parts) > 1:
                    celex = parts[1].split("&")[0]

            items.append(
                {
                    "title": title,
                    "link": link,
                    "description": desc,
                    "pub_date": pub_date,
                    "guid": guid,
                    "celex": celex,
                }
            )

        return items

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over CELEX / GUID and title."""
        identity = {
            "guid": raw.get("guid") or raw.get("celex"),
            "title": (raw.get("title") or "").strip().lower(),
            "pub_date": raw.get("pub_date"),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw EUR-Lex feed item."""
        title = (raw.get("title") or "").strip()
        link = canonicalize_url(raw.get("link"))
        guid = (raw.get("guid") or "").strip()
        celex = (raw.get("celex") or guid).strip()

        pub_date = None
        pub_str = raw.get("pub_date")
        if pub_str:
            try:
                pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
            except Exception:
                pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=celex or chash[:16],
            content_hash=chash,
            canonical_url=link,
            title=f"EUR-Lex Act: {title}",
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "celex": celex,
                "title": title,
                "description": raw.get("description"),
                "url": link,
                "jurisdiction": "EU",
            },
        )
