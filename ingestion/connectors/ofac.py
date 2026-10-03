"""
OFAC Sanctions List Service (SLS) connector.
Architecture reference: §E.1 #1, §F.2, §F.3.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class OFACConnector(SourceConnector):
    """
    US Treasury OFAC Sanctions List Service (SLS) connector.
    Downloads and parses SDN & Consolidated sanctions lists.
    """

    source_id: str = "ofac_sls"
    source_type: str = "bulk_download"
    reliability: str = "high"

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ofac_sls_base_url).rstrip("/")

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """
        Fetches the active SDN XML list from OFAC SLS.
        Enumerates /sanctions-lists to get current filename per §E.1 #1.
        """
        headers = {"Accept": "application/xml, text/xml, */*"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Enumerate available lists
            list_url = f"{self.base_url}/api/sanctions-lists"
            download_url = f"{self.base_url}/api/download/sdn.xml"
            try:
                resp = await client.get(list_url, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    lists_data = resp.json()
                    # Find sdn.xml entry if present
                    for item in lists_data if isinstance(lists_data, list) else []:
                        if "sdn.xml" in str(item).lower():
                            fn = item.get("fileName") or item.get("filename") or "sdn.xml"
                            download_url = f"{self.base_url}/api/download/{fn}"
                            break
            except Exception:
                # Fallback to direct default endpoint
                pass

            resp = await client.get(download_url, headers=headers)
            resp.raise_for_status()
            raw_xml = resp.text

        items = self.parse_xml_entries(raw_xml)
        return FetchResult(
            items=items,
            next_cursor=None,
            metadata={"total_entries": len(items), "source": "ofac_sls"},
        )

    def parse_xml_entries(self, xml_content: str) -> list[dict[str, Any]]:
        """Parses OFAC XML string into raw item dictionaries."""
        root = ET.fromstring(xml_content)
        # Strip XML namespaces for uniform querying
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        entries: list[dict[str, Any]] = []
        for sdn in root.findall(".//sdnEntry"):
            uid = sdn.findtext("uid", "").strip()
            first_name = sdn.findtext("firstName", "").strip()
            last_name = sdn.findtext("lastName", "").strip()
            full_name = f"{first_name} {last_name}".strip() if first_name else last_name
            sdn_type = sdn.findtext("sdnType", "Entity").strip()
            remarks = sdn.findtext("remarks", "").strip()

            programs = [
                p.text.strip()
                for p in sdn.findall(".//programList/program")
                if p.text and p.text.strip()
            ]

            aliases = [
                a.findtext("lastName", "").strip()
                for a in sdn.findall(".//akaList/aka")
                if a.findtext("lastName")
            ]

            addresses: list[dict[str, str]] = []
            for addr in sdn.findall(".//addressList/address"):
                addresses.append(
                    {
                        "address": addr.findtext("address1", "").strip(),
                        "city": addr.findtext("city", "").strip(),
                        "state_province": addr.findtext("stateOrProvince", "").strip(),
                        "country": addr.findtext("country", "").strip(),
                    }
                )

            id_docs: list[dict[str, str]] = []
            for doc in sdn.findall(".//idList/id"):
                id_docs.append(
                    {
                        "type": doc.findtext("idType", "").strip(),
                        "number": doc.findtext("idNumber", "").strip(),
                        "country": doc.findtext("idCountry", "").strip(),
                    }
                )

            entries.append(
                {
                    "uid": uid,
                    "first_name": first_name,
                    "last_name": last_name,
                    "name": full_name,
                    "type": sdn_type,
                    "remarks": remarks,
                    "programs": sorted(programs),
                    "aliases": sorted(aliases),
                    "addresses": addresses,
                    "id_documents": id_docs,
                    "raw_xml_snippet": ET.tostring(sdn, encoding="unicode"),
                }
            )

        return entries

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over identity fields."""
        identity = {
            "uid": raw.get("uid"),
            "name": raw.get("name"),
            "type": raw.get("type"),
            "programs": sorted(raw.get("programs", [])),
            "aliases": sorted(raw.get("aliases", [])),
            "addresses": sorted(
                str(a.get("country", "") + ":" + a.get("city", ""))
                for a in raw.get("addresses", [])
            ),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of raw OFAC entry."""
        uid = str(raw.get("uid", "")).strip()
        name = raw.get("name", "").strip()
        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=f"ofac-{uid}" if uid else f"ofac-{chash[:16]}",
            content_hash=chash,
            canonical_url=f"https://sanctionssearch.ofac.treas.gov/Details.aspx?id={uid}" if uid else None,
            title=f"OFAC Sanctions: {name} ({raw.get('type', 'Entity')})",
            published_date=datetime.now().date(),
            source_type="live",
            reliability="high",
            language="en",
            raw_payload=raw,
            normalized_data={
                "uid": uid,
                "name": name,
                "entity_type": raw.get("type", "Entity"),
                "programs": raw.get("programs", []),
                "aliases": raw.get("aliases", []),
                "addresses": raw.get("addresses", []),
                "id_documents": raw.get("id_documents", []),
                "remarks": raw.get("remarks"),
                "jurisdictions": list(
                    {
                        addr.get("country", "")
                        for addr in raw.get("addresses", [])
                        if addr.get("country")
                    }
                ),
            },
        )
