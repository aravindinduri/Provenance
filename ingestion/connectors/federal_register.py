"""
Federal Register API (US) connector.
Architecture reference: §E.1 #4, §F.2, §F.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import canonicalize_url, compute_content_hash


class FederalRegisterConnector(SourceConnector):
    """
    US Federal Register API connector.
    Monitors Commerce (BIS), Treasury (OFAC), and State export controls and notices.
    """

    source_id: str = "federal_register"
    source_type: str = "api"
    reliability: str = "high"

    DEFAULT_AGENCIES = ["commerce-department", "treasury-department", "state-department"]
    DEFAULT_TYPES = ["RULE", "PRORULE", "NOTICE", "PRESDOCU"]

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.federal_register_base_url).rstrip("/")

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """
        Fetches documents from Federal Register API.
        Cursor can be a next URL or page number.
        """
        endpoint = cursor if cursor and cursor.startswith("http") else f"{self.base_url}/documents.json"
        params: dict[str, Any] = {}

        if not (cursor and cursor.startswith("http")):
            params = {
                "per_page": 50,
                "order": "newest",
                "conditions[agencies][]": self.DEFAULT_AGENCIES,
                "conditions[type][]": self.DEFAULT_TYPES,
            }

        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(endpoint, params=params, headers=headers)
            resp.raise_for_status()
            payload = resp.json()

        results = payload.get("results", []) if isinstance(payload, dict) else []
        next_cursor = payload.get("next_page_url")

        return FetchResult(
            items=results,
            next_cursor=next_cursor,
            metadata={"count": payload.get("count", len(results))},
        )

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over identity and revision fields."""
        doc_num = str(raw.get("document_number", "")).strip()
        identity = {
            "document_number": doc_num,
            "title": (raw.get("title") or "").strip().lower(),
            "publication_date": raw.get("publication_date"),
            "effective_on": raw.get("effective_on"),
            "abstract": (raw.get("abstract") or "").strip()[:500],
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw Federal Register document item."""
        doc_num = str(raw.get("document_number", "")).strip()
        title = (raw.get("title") or "").strip()
        html_url = canonicalize_url(raw.get("html_url"))

        pub_date = None
        pub_str = raw.get("publication_date")
        if pub_str:
            try:
                pub_date = datetime.strptime(pub_str, "%Y-%m-%d").date()
            except Exception:
                pass

        effective_date = None
        eff_str = raw.get("effective_on")
        if eff_str:
            try:
                effective_date = datetime.strptime(eff_str, "%Y-%m-%d").date()
            except Exception:
                pass

        agencies = [
            a.get("name") or a.get("raw_name")
            for a in raw.get("agencies", [])
            if isinstance(a, dict)
        ]

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=doc_num,
            content_hash=chash,
            canonical_url=html_url,
            title=f"Federal Register [{raw.get('type', 'Notice')}]: {title}",
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "document_number": doc_num,
                "title": title,
                "type": raw.get("type"),
                "abstract": raw.get("abstract"),
                "agencies": agencies,
                "effective_on": str(effective_date) if effective_date else None,
                "html_url": html_url,
                "pdf_url": raw.get("pdf_url"),
                "topics": raw.get("topics", []),
                "jurisdiction": "US",
            },
        )
