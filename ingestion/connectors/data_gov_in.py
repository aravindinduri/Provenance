"""
India Open Government Data (data.gov.in) connector.
Architecture reference: §E.1 #9, §F.2, §F.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class DataGovInConnector(SourceConnector):
    """
    Government of India Open Government Data (OGD) Platform connector.
    Fetches MCA company master data and trade statistics.
    Monitors X-RateLimit-* response headers.
    """

    source_id: str = "data_gov_in"
    source_type: str = "api"
    reliability: str = "high"

    DEFAULT_BASE_URL = "https://api.data.gov.in/resource"
    DEFAULT_RESOURCE_ID = "6176ee09-3d56-4a3b-8115-238ad579b153"  # default sample resource

    def __init__(self, resource_id: str | None = None, base_url: str | None = None) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.resource_id = resource_id or self.DEFAULT_RESOURCE_ID

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Fetches records from data.gov.in API with key and pagination offset."""
        settings = get_settings()
        api_key = settings.data_gov_in_api_key

        offset = int(cursor) if cursor and cursor.isdigit() else 0
        limit = 50

        endpoint = f"{self.base_url}/{self.resource_id}"
        params: dict[str, Any] = {
            "format": "json",
            "offset": offset,
            "limit": limit,
        }
        if api_key:
            params["api-key"] = api_key

        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(endpoint, params=params, headers=headers)
            # Check rate limit headers
            rate_remaining = resp.headers.get("X-RateLimit-Remaining")
            if resp.status_code == 429:
                from ingestion.connectors.rate_limiter import get_token_bucket_limiter
                await get_token_bucket_limiter().record_429("data_gov_in", 60.0)
            resp.raise_for_status()
            payload = resp.json()

        records = payload.get("records", []) if isinstance(payload, dict) else []
        total = payload.get("total", len(records)) if isinstance(payload, dict) else len(records)
        next_offset = offset + limit if (offset + limit) < total else None

        return FetchResult(
            items=records,
            next_cursor=str(next_offset) if next_offset is not None else None,
            metadata={"total": total, "rate_limit_remaining": rate_remaining},
        )

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over MCA company record or commodity record."""
        cin = raw.get("cin") or raw.get("registration_number") or raw.get("record_id")
        identity = {
            "id": cin,
            "company_name": (raw.get("company_name") or raw.get("commodity") or "").strip().lower(),
            "status": raw.get("status"),
            "date": raw.get("date_of_incorporation") or raw.get("arrival_date"),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw data.gov.in record."""
        cin = str(raw.get("cin") or raw.get("registration_number") or "").strip()
        company_name = str(raw.get("company_name") or raw.get("commodity") or "Record").strip()

        pub_date = None
        date_str = raw.get("date_of_incorporation") or raw.get("arrival_date")
        if date_str:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    pub_date = datetime.strptime(str(date_str).strip()[:10], fmt).date()
                    break
                except Exception:
                    pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=cin or f"govin-{chash[:16]}",
            content_hash=chash,
            canonical_url=f"https://data.gov.in/resource/{self.resource_id}",
            title=f"India MCA / OGD: {company_name}" + (f" ({cin})" if cin else ""),
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "cin": cin,
                "company_name": company_name,
                "roc": raw.get("roc"),
                "status": raw.get("status"),
                "class_of_company": raw.get("class_of_company"),
                "authorized_capital": raw.get("authorized_capital"),
                "paid_up_capital": raw.get("paid_up_capital"),
                "registered_address": raw.get("registered_address"),
                "email": raw.get("email"),
                "jurisdiction": "IN",
            },
        )
