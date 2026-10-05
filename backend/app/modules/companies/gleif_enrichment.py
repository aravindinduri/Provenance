"""
app/modules/companies/gleif_enrichment.py — GLEIF Level-2 corporate hierarchy enrichment.

Architecture reference: §E.1 #2, §G.1, §8 (Phase 9).
Seeds `owned_by` edges into the tenant's supplier graph from GLEIF direct/ultimate parent data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.modules.companies.models import Company, CompanyIdentifier
from app.modules.companies.normalizer import normalize_company_name
from app.modules.graph.models import SupplierRelationship

logger = structlog.get_logger(__name__)


class GleifEnrichmentService:
    def __init__(self, db: AsyncSession, base_url: str | None = None) -> None:
        self.db = db
        settings = get_settings()
        self.base_url = (base_url or settings.gleif_base_url).rstrip("/")

    async def fetch_lei_record(self, lei: str) -> dict[str, Any] | None:
        """Fetch LEI record directly by LEI code."""
        url = f"{self.base_url}/lei-records/{lei}"
        headers = {"Accept": "application/vnd.api+json", "User-Agent": "Provenance/1.0"}
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json().get("data")
                return None
        except Exception as exc:
            logger.warning("gleif_fetch_by_lei_failed", lei=lei, error=str(exc))
            return None

    async def search_lei_by_name(self, name: str, country: str | None = None) -> dict[str, Any] | None:
        """Search GLEIF API by legal name."""
        url = f"{self.base_url}/lei-records"
        params: dict[str, Any] = {"filter[entity.legalName]": name, "page[size]": 1}
        headers = {"Accept": "application/vnd.api+json", "User-Agent": "Provenance/1.0"}
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    return data[0] if data else None
                return None
        except Exception as exc:
            logger.warning("gleif_search_by_name_failed", name=name, error=str(exc))
            return None

    async def enrich_company(
        self,
        company_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Enrich company profile and seed Level-2 owned_by hierarchy edges.
        """
        stmt = (
            select(Company)
            .where(Company.id == company_id, Company.deleted_at.is_(None))
            .options(selectinload(Company.identifiers))
        )
        res = await self.db.execute(stmt)
        company = res.scalar_one_or_none()
        if not company:
            return {"status": "error", "message": f"Company {company_id} not found"}

        # 1. Check existing LEI identifier
        lei_id: str | None = None
        for ident in company.identifiers or []:
            if ident.identifier_type.lower() == "lei":
                lei_id = ident.identifier_value.strip().upper()
                break

        # 2. Fetch record from GLEIF
        gleif_record: dict[str, Any] | None = None
        if lei_id:
            gleif_record = await self.fetch_lei_record(lei_id)
        else:
            gleif_record = await self.search_lei_by_name(company.legal_name, company.country)
            if gleif_record:
                attr = gleif_record.get("attributes", {})
                lei_id = attr.get("lei") or gleif_record.get("id")

        if not gleif_record:
            company.enrichment_status = "not_found"
            await self.db.flush()
            return {"status": "not_found", "company_id": str(company_id)}

        attributes = gleif_record.get("attributes", {})
        entity = attributes.get("entity", {})
        relationships = gleif_record.get("relationships", {})

        # Ensure LEI identifier is saved
        if lei_id and not any(i.identifier_type.lower() == "lei" for i in (company.identifiers or [])):
            lei_ident = CompanyIdentifier(
                company_id=company.id,
                identifier_type="lei",
                identifier_value=lei_id,
                issuing_country=entity.get("jurisdiction", "")[:2] if entity.get("jurisdiction") else None,
                source="gleif",
                verified_at=datetime.now(timezone.utc),
            )
            self.db.add(lei_ident)

        # Update company metadata
        company.enrichment_status = "enriched"
        company.last_enriched_at = datetime.now(timezone.utc)
        if not company.jurisdiction and entity.get("jurisdiction"):
            company.jurisdiction = str(entity.get("jurisdiction"))[:100]
        if not company.legal_form and entity.get("legalForm", {}).get("name"):
            company.legal_form = str(entity.get("legalForm", {}).get("name"))[:100]

        # 3. Extract parent relationships (Level 2)
        direct_parent_lei = (
            relationships.get("direct-parent", {})
            .get("data", {})
            .get("id")
        )
        ultimate_parent_lei = (
            relationships.get("ultimate-parent", {})
            .get("data", {})
            .get("id")
        )

        parents_seeded: list[dict[str, Any]] = []

        # Find which tenant org_ids need this edge seeded
        target_org_ids: set[uuid.UUID] = set()
        if org_id:
            target_org_ids.add(org_id)
        else:
            # Query all orgs that have a relationship with this company
            sr_stmt = select(SupplierRelationship.org_id).where(
                SupplierRelationship.from_company_id == company.id,
                SupplierRelationship.deleted_at.is_(None),
            )
            sr_res = await self.db.execute(sr_stmt)
            for oid in sr_res.scalars().all():
                target_org_ids.add(oid)

        parent_leis = [p for p in [direct_parent_lei, ultimate_parent_lei] if p and p != lei_id]

        for p_lei in parent_leis:
            parent_comp = await self._get_or_create_parent_company(p_lei)
            if not parent_comp:
                continue

            for t_org_id in target_org_ids:
                # Check if relationship already exists
                edge_stmt = select(SupplierRelationship).where(
                    SupplierRelationship.org_id == t_org_id,
                    SupplierRelationship.from_company_id == company.id,
                    SupplierRelationship.to_company_id == parent_comp.id,
                    SupplierRelationship.relationship_type == "owned_by",
                    SupplierRelationship.valid_to.is_(None),
                )
                edge_res = await self.db.execute(edge_stmt)
                existing_edge = edge_res.scalar_one_or_none()

                if not existing_edge:
                    new_edge = SupplierRelationship(
                        org_id=t_org_id,
                        from_company_id=company.id,
                        to_company_id=parent_comp.id,
                        relationship_type="owned_by",
                        source="gleif",
                        confidence=1.0,
                        tier=1,
                        criticality=3,
                    )
                    self.db.add(new_edge)
                    parents_seeded.append({
                        "org_id": str(t_org_id),
                        "parent_id": str(parent_comp.id),
                        "parent_name": parent_comp.legal_name,
                        "parent_lei": p_lei,
                    })

        await self.db.flush()
        return {
            "status": "enriched",
            "company_id": str(company.id),
            "lei": lei_id,
            "parents_seeded": parents_seeded,
        }

    async def _get_or_create_parent_company(self, parent_lei: str) -> Company | None:
        """Find or create parent company given its LEI."""
        stmt = (
            select(Company)
            .join(CompanyIdentifier, Company.id == CompanyIdentifier.company_id)
            .where(
                CompanyIdentifier.identifier_type == "lei",
                CompanyIdentifier.identifier_value.ilike(parent_lei),
                Company.deleted_at.is_(None),
            )
            .limit(1)
        )
        res = await self.db.execute(stmt)
        comp = res.scalar_one_or_none()
        if comp:
            return comp

        # Fetch parent details from GLEIF
        parent_raw = await self.fetch_lei_record(parent_lei)
        legal_name = f"Parent Entity ({parent_lei})"
        country = None
        jurisdiction = None

        if parent_raw:
            attr = parent_raw.get("attributes", {})
            ent = attr.get("entity", {})
            legal_name = ent.get("legalName", {}).get("name") or legal_name
            jurisdiction = ent.get("jurisdiction")
            country = jurisdiction[:2] if jurisdiction else None

        norm_name = normalize_company_name(legal_name)
        new_company = Company(
            legal_name=legal_name,
            name_norm=norm_name,
            country=country,
            jurisdiction=str(jurisdiction)[:100] if jurisdiction else None,
            data_source="gleif",
            enrichment_status="enriched",
            last_enriched_at=datetime.now(timezone.utc),
            confidence=1.0,
            is_verified=True,
        )
        self.db.add(new_company)
        await self.db.flush()

        # Add LEI identifier
        p_ident = CompanyIdentifier(
            company_id=new_company.id,
            identifier_type="lei",
            identifier_value=parent_lei,
            issuing_country=country,
            source="gleif",
            verified_at=datetime.now(timezone.utc),
        )
        self.db.add(p_ident)
        await self.db.flush()
        return new_company
