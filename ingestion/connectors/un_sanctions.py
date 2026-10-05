"""
UN Security Council Consolidated List connector.
Architecture reference: §E.1 #7, §F.2, §F.3.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class UNSanctionsConnector(SourceConnector):
    """
    United Nations Security Council Consolidated Sanctions List connector.
    Downloads the official XML list containing all individuals and entities.
    """

    source_id: str = "un_sanctions"
    source_type: str = "bulk_download"
    reliability: str = "high"

    DEFAULT_XML_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

    def __init__(self, xml_url: str | None = None) -> None:
        self.xml_url = xml_url or self.DEFAULT_XML_URL

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Downloads UN SC XML list."""
        headers = {"Accept": "application/xml, text/xml, */*"}
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(self.xml_url, headers=headers)
            resp.raise_for_status()
            content = resp.text

        items = self.parse_xml(content)
        return FetchResult(
            items=items,
            next_cursor=None,
            metadata={"count": len(items)},
        )

    def parse_xml(self, xml_content: str) -> list[dict[str, Any]]:
        """Parses UN SC XML format."""
        root = ET.fromstring(xml_content)
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        entries: list[dict[str, Any]] = []

        # 1. Individuals
        for ind in root.findall(".//INDIVIDUAL"):
            dataid = ind.findtext("DATAID", "").strip()
            first_name = ind.findtext("FIRST_NAME", "").strip()
            second_name = ind.findtext("SECOND_NAME", "").strip()
            full_name = f"{first_name} {second_name}".strip()
            list_type = ind.findtext("UN_LIST_TYPE", "").strip()
            ref_num = ind.findtext("REFERENCE_NUMBER", "").strip()
            listed_on = ind.findtext("LISTED_ON", "").strip()
            comments = ind.findtext("COMMENTS_NOTES", "").strip()

            nationality = ind.findtext(".//NATIONALITY/VALUE", "").strip()
            aliases = [
                a.findtext("ALIAS_NAME", "").strip()
                for a in ind.findall(".//INDIVIDUAL_ALIAS")
                if a.findtext("ALIAS_NAME")
            ]

            entries.append(
                {
                    "dataid": dataid,
                    "name": full_name,
                    "type": "Individual",
                    "list_type": list_type,
                    "reference_number": ref_num,
                    "listed_on": listed_on,
                    "comments": comments,
                    "nationality": nationality,
                    "aliases": aliases,
                }
            )

        # 2. Entities
        for ent in root.findall(".//ENTITY"):
            dataid = ent.findtext("DATAID", "").strip()
            name = ent.findtext("FIRST_NAME", "").strip()
            list_type = ent.findtext("UN_LIST_TYPE", "").strip()
            ref_num = ent.findtext("REFERENCE_NUMBER", "").strip()
            listed_on = ent.findtext("LISTED_ON", "").strip()
            comments = ent.findtext("COMMENTS_NOTES", "").strip()

            country = ent.findtext(".//ENTITY_ADDRESS/COUNTRY", "").strip()
            city = ent.findtext(".//ENTITY_ADDRESS/CITY", "").strip()

            entries.append(
                {
                    "dataid": dataid,
                    "name": name,
                    "type": "Entity",
                    "list_type": list_type,
                    "reference_number": ref_num,
                    "listed_on": listed_on,
                    "comments": comments,
                    "country": country,
                    "city": city,
                }
            )

        return entries

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over UN SC identity."""
        identity = {
            "dataid": raw.get("dataid"),
            "ref_num": raw.get("reference_number"),
            "name": (raw.get("name") or "").strip().lower(),
            "list_type": raw.get("list_type"),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw UN sanctions item."""
        dataid = str(raw.get("dataid", "")).strip()
        ref_num = str(raw.get("reference_number", "")).strip()
        name = raw.get("name", "").strip()

        pub_date = None
        listed_str = raw.get("listed_on")
        if listed_str:
            try:
                pub_date = datetime.strptime(listed_str[:10], "%Y-%m-%d").date()
            except Exception:
                pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=f"un-{dataid}" if dataid else f"un-{ref_num or chash[:16]}",
            content_hash=chash,
            canonical_url=f"https://www.un.org/securitycouncil/sanctions/{raw.get('list_type', 'consolidated')}",
            title=f"UN SC Sanctions [{raw.get('list_type', 'UN')}]: {name} ({raw.get('type', 'Entity')})",
            published_date=pub_date,
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "dataid": dataid,
                "reference_number": ref_num,
                "name": name,
                "entity_type": raw.get("type", "Entity"),
                "list_type": raw.get("list_type"),
                "listed_on": listed_str,
                "comments": raw.get("comments"),
                "country": raw.get("country") or raw.get("nationality"),
                "aliases": raw.get("aliases", []),
            },
        )
