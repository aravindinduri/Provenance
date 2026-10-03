"""
GDELT DOC 2.0 API connector.
Architecture reference: §E.1 #3, §F.2, §F.3, §F.4 (GDELT global token bucket at 6s).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from ingestion.connectors.base import FetchResult, NewsConnector, NormalizedRecord
from ingestion.connectors.rate_limiter import get_token_bucket_limiter
from ingestion.connectors.utils import canonicalize_url, compute_content_hash


class GDELTConnector(NewsConnector):
    """
    GDELT DOC 2.0 API connector for worldwide news monitoring.
    Enforces a strict 6-second global rate limit and handles 429 cooldowns.
    Implements NewsConnector protocol for plug-and-play news evaluation.
    """

    source_id: str = "gdelt_doc"
    source_type: str = "api"
    reliability: str = "medium"

    DEFAULT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.rate_limiter = get_token_bucket_limiter()

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """
        Default fetch: searches for global supply chain disruption and export restrictions.
        """
        query = '("export ban" OR "export control" OR "export restriction" OR "sanctions" OR "insolvency" OR "force majeure")'
        return await self.search_news(query=query, cursor=cursor)

    async def search_news(
        self,
        query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        cursor: str | None = None,
    ) -> FetchResult:
        """
        Query GDELT DOC 2.0 ArtList API with query terms and rate-limit guard.
        """
        settings = get_settings()

        # Enforce global rate limiter (minimum 6s interval across all workers)
        await self.rate_limiter.acquire(
            key="gdelt_doc",
            min_interval_seconds=float(settings.gdelt_min_request_interval_seconds),
            fail_fast=False,
        )

        params: dict[str, Any] = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 50,
            "sort": "DateDesc",
        }
        if start_date:
            params["startdatetime"] = start_date
        if end_date:
            params["enddatetime"] = end_date

        headers = {
            "User-Agent": settings.gdelt_user_agent,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.endpoint, params=params, headers=headers)
            if resp.status_code == 429:
                await self.rate_limiter.record_429("gdelt_doc", cooldown_seconds=30.0)
                resp.raise_for_status()

            resp.raise_for_status()
            payload = resp.json()

        articles = payload.get("articles", []) if isinstance(payload, dict) else []

        return FetchResult(
            items=articles,
            next_cursor=None,
            metadata={"query": query, "article_count": len(articles)},
        )

    def content_hash(self, raw: dict[str, Any]) -> str:
        """
        Stable sha256 over identity fields: canonical URL, title, seendate.
        """
        raw_url = raw.get("url", "")
        canon_url = canonicalize_url(raw_url) or raw_url
        title = (raw.get("title") or "").strip().lower()
        seendate = str(raw.get("seendate") or "").strip()

        identity = {
            "canonical_url": canon_url,
            "title": title,
            "seendate": seendate,
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """
        Pure normalization of GDELT article metadata per §E.1 #3 & §F.3.
        Stores ONLY URL, title, domain, seendate, language, sourcecountry.
        Does NOT store or re-serve full article text.
        """
        raw_url = raw.get("url", "")
        canon_url = canonicalize_url(raw_url) or raw_url
        title = (raw.get("title") or "").strip()
        seendate_str = str(raw.get("seendate") or "").strip()

        pub_date = None
        if seendate_str and len(seendate_str) >= 8:
            try:
                # GDELT date format: YYYYMMDDTHHMMSSZ or YYYYMMDD
                pub_date = datetime.strptime(seendate_str[:8], "%Y%m%d").date()
            except Exception:
                pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=canon_url,
            content_hash=chash,
            canonical_url=canon_url,
            title=title,
            published_date=pub_date,
            source_type="live",
            reliability="medium",
            language=raw.get("language", "en"),
            raw_payload={
                "url": raw_url,
                "title": title,
                "domain": raw.get("domain"),
                "seendate": seendate_str,
                "language": raw.get("language"),
                "sourcecountry": raw.get("sourcecountry"),
            },
            normalized_data={
                "url": canon_url,
                "title": title,
                "domain": raw.get("domain"),
                "source_country": raw.get("sourcecountry"),
                "language": raw.get("language"),
                "seendate": seendate_str,
            },
        )
