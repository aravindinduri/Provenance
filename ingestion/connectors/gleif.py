"""
GLEIF LEI API connector.
Architecture reference: §E.1 #2, §F.2, §F.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class GLEIFConnector(SourceConnector):
    """
    Global Legal Entity Identifier Foundation (GLEIF) API connector.
    Enriches legal entities and seeds Level-2 corporate hierarchy.
    """

    source_id: str = "gleif"
    source_type: str = "api"
    reliability: str = "high"

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.gleif_base_url).rstrip("/")

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """
        Fetches LEI records from GLEIF API.
        Cursor can be a page number or next URL.
        """
        endpoint = cursor if cursor and cursor.startswith("http") else f"{self.base_url}/lei-records"
        params = {} if cursor and cursor.startswith("http") else {"page[size]": 50}

        headers = {
            "Accept": "application/vnd.api+json",
            "User-Agent": "Provenance/1.0 (supply-chain-risk)",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(endpoint, params=params, headers=headers)
            if resp.status_code == 429:
                from ingestion.connectors.rate_limiter import get_token_bucket_limiter
                await get_token_bucket_limiter().record_429("gleif", 30.0)
            resp.raise_for_status()
            payload = resp.json()

        items = payload.get("data", [])
        next_cursor = None
        links = payload.get("links", {})
        if "next" in links and links["next"]:
            next_cursor = links["next"]

        return FetchResult(
            items=items,
            next_cursor=next_cursor,
            metadata={"total": payload.get("meta", {}).get("pagination", {}).get("total")},
        )

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over canonical LEI identity fields."""
        attributes = raw.get("attributes", {})
        entity = attributes.get("entity", {})
        legal_name = entity.get("legalName", {}).get("name", "")
        lei = attributes.get("lei") or raw.get("id", "")
        relationships = raw.get("relationships", {})

        direct_parent = (
            relationships.get("direct-parent", {})
            .get("data", {})
            .get("id")
        )
        ultimate_parent = (
            relationships.get("ultimate-parent", {})
            .get("data", {})
            .get("id")
        )

        identity = {
            "lei": lei,
            "legal_name": legal_name.strip().lower(),
            "jurisdiction": entity.get("jurisdiction", ""),
            "status": entity.get("status", ""),
            "direct_parent": direct_parent,
            "ultimate_parent": ultimate_parent,
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw GLEIF JSON:API item."""
        attributes = raw.get("attributes", {})
        entity = attributes.get("entity", {})
        registration = attributes.get("registration", {})
        relationships = raw.get("relationships", {})

        lei = attributes.get("lei") or raw.get("id", "")
        legal_name = entity.get("legalName", {}).get("name", "").strip()

        # Parse published/update date
        last_update_str = registration.get("lastUpdateDate")
        pub_date = None
        if last_update_str:
            try:
                pub_date = datetime.fromisoformat(last_update_str.replace("Z", "+00:00")).date()
            except Exception:
                pass

        direct_parent = (
            relationships.get("direct-parent", {})
            .get("data", {})
            .get("id")
        )
        ultimate_parent = (
            relationships.get("ultimate-parent", {})
            .get("data", {})
            .get("id")
        )

        other_names = [
            on.get("name", "") for on in entity.get("otherNames", []) if on.get("name")
        ]

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=lei,
            content_hash=chash,
            canonical_url=f"https://search.gleif.org/#/record/{lei}",
            title=f"GLEIF Entity: {legal_name} ({lei})",
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language=entity.get("legalName", {}).get("language", "en"),
            raw_payload=raw,
            normalized_data={
                "lei": lei,
                "legal_name": legal_name,
                "other_names": other_names,
                "jurisdiction": entity.get("jurisdiction"),
                "status": entity.get("status"),
                "registration_status": registration.get("status"),
                "next_renewal_date": registration.get("nextRenewalDate"),
                "legal_address": entity.get("legalAddress"),
                "headquarters_address": entity.get("headquartersAddress"),
                "direct_parent_lei": direct_parent,
                "ultimate_parent_lei": ultimate_parent,
                "bic": attributes.get("bic", []),
            },
        )
