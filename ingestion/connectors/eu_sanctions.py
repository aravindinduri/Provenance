"""
EU Consolidated Financial Sanctions List connector.
Architecture reference: §E.1 #6, §F.2, §F.3.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class EUSanctionsConnector(SourceConnector):
    """
    EU Consolidated Financial Sanctions List (FSF) connector.
    Downloads asset-freeze designations published by the European Commission.
    NOTE: Coverage gap: Annex IV of Regulation 833/2014 entities are not included.
    """

    source_id: str = "eu_sanctions"
    source_type: str = "bulk_download"
    reliability: str = "high"

    COVERAGE_GAP_NOTE = (
        "Annex IV of Regulation 833/2014 entities are subject to specific "
        "economic prohibitions but NOT asset freezes, and are therefore NOT in this list."
    )

    DEFAULT_DOWNLOAD_URL = (
        "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
    )

    def __init__(self, download_url: str | None = None) -> None:
        self.download_url = download_url or self.DEFAULT_DOWNLOAD_URL

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Downloads full sanctions list XML."""
        settings = get_settings()
        params = {}
        if settings.eu_sanctions_token:
            params["token"] = settings.eu_sanctions_token

        headers = {"Accept": "application/xml, text/xml, */*"}
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(self.download_url, params=params, headers=headers)
            resp.raise_for_status()
            content = resp.text

        items = self.parse_xml(content)
        return FetchResult(
            items=items,
            next_cursor=None,
            metadata={"count": len(items)},
        )

    def parse_xml(self, xml_content: str) -> list[dict[str, Any]]:
        """Parses EU FSF XML format."""
        root = ET.fromstring(xml_content)
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        entities: list[dict[str, Any]] = []
        for se in root.findall(".//sanctionEntity"):
            logical_id = se.get("logicalId", "").strip()
            reg_elem = se.find("regulation")
            legal_basis = reg_elem.get("legalBasis", "") if reg_elem is not None else ""
            pub_date = reg_elem.get("publicationDate", "") if reg_elem is not None else ""

            subj_type = se.findtext("subjectType", "Entity").strip()
            name_elem = se.find("nameAlias")
            name = (
                name_elem.get("wholeName", "")
                if name_elem is not None
                else se.findtext("nameAlias", "")
            ).strip()

            addr_elem = se.find("address")
            country_iso2 = ""
            city = ""
            if addr_elem is not None:
                country_iso2 = addr_elem.get("countryIso2Code", "")
                city = addr_elem.get("city", "")

            sanction_type = se.findtext("sanctionType", "Asset freeze").strip()

            entities.append(
                {
                    "logical_id": logical_id,
                    "name": name,
                    "subject_type": subj_type,
                    "legal_basis": legal_basis,
                    "publication_date": pub_date,
                    "country_iso2": country_iso2,
                    "city": city,
                    "sanction_type": sanction_type,
                }
            )

        return entities

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over EU sanctions entity."""
        identity = {
            "logical_id": raw.get("logical_id"),
            "name": (raw.get("name") or "").strip().lower(),
            "legal_basis": raw.get("legal_basis"),
            "country_iso2": raw.get("country_iso2"),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw EU sanctions item."""
        logical_id = str(raw.get("logical_id", "")).strip()
        name = raw.get("name", "").strip()

        pub_date = None
        pub_str = raw.get("publication_date")
        if pub_str:
            try:
                pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
            except Exception:
                pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=f"eu-{logical_id}" if logical_id else f"eu-{chash[:16]}",
            content_hash=chash,
            canonical_url=f"https://www.sanctionsmap.eu/#/main?search={{%22entity%22:%22{logical_id}%22}}",
            title=f"EU Sanctions: {name} ({raw.get('subject_type', 'Entity')})",
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "logical_id": logical_id,
                "name": name,
                "subject_type": raw.get("subject_type"),
                "legal_basis": raw.get("legal_basis"),
                "country": raw.get("country_iso2"),
                "city": raw.get("city"),
                "sanction_type": raw.get("sanction_type"),
                "coverage_notes": self.COVERAGE_GAP_NOTE,
                "jurisdictions": [raw.get("country_iso2")] if raw.get("country_iso2") else [],
            },
        )
