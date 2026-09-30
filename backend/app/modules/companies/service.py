"""
app/modules/companies/service.py — Business logic for the companies module.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.models import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import (
    CompanyAliasOut,
    CompanyDetailOut,
    CompanyIdentifierOut,
    CompanyLocationOut,
    CompanySummaryOut,
    LocationOut,
)


class CompanyNotFound(Exception):
    def __init__(self, company_id: uuid.UUID) -> None:
        super().__init__(f"Company {company_id} not found")
        self.company_id = company_id


class CompanyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CompanyRepository(db)

    async def search_companies(
        self,
        *,
        q: str | None = None,
        country: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Company], str | None, bool]:
        """Search canonical companies using cursor pagination."""
        return await self.repo.search(
            q=q,
            country=country,
            cursor=cursor,
            limit=limit,
        )

    async def get_company(self, company_id: uuid.UUID) -> Company:
        """Get company model or raise CompanyNotFound."""
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFound(company_id)
        return company

    async def get_company_detail(self, company_id: uuid.UUID) -> CompanyDetailOut:
        """Get enriched company profile including identifiers, aliases, and locations."""
        company = await self.get_company(company_id)
        locations = await self.repo.get_locations_for_company(company_id)

        loc_outs = [
            CompanyLocationOut(
                id=cl.id,
                site_type=cl.site_type,
                is_primary=cl.is_primary,
                source=cl.source,
                confidence=float(cl.confidence),
                valid_from=cl.valid_from,
                valid_to=cl.valid_to,
                location=LocationOut.model_validate(cl.location),
            )
            for cl in locations
        ]

        id_outs = [
            CompanyIdentifierOut.model_validate(ci)
            for ci in (company.identifiers or [])
        ]

        alias_outs = [
            CompanyAliasOut.model_validate(ca)
            for ca in (company.aliases or [])
        ]

        summary = CompanySummaryOut.model_validate(company)
        return CompanyDetailOut(
            **summary.model_dump(),
            registered_address=company.registered_address,
            hq_address=company.hq_address,
            last_enriched_at=company.last_enriched_at,
            identifiers=id_outs,
            aliases=alias_outs,
            locations=loc_outs,
        )

    async def get_or_create_by_name(
        self,
        *,
        legal_name: str,
        country: str | None = None,
        primary_domain: str | None = None,
        jurisdiction: str | None = None,
        industry_codes: list[str] | None = None,
    ) -> Company:
        """Look up by exact name/norm; if not found, create a new canonical record."""
        existing = await self.repo.get_by_exact_name(legal_name)
        if existing:
            return existing

        return await self.repo.create(
            legal_name=legal_name,
            country=country,
            primary_domain=primary_domain,
            jurisdiction=jurisdiction,
            industry_codes=industry_codes,
            data_source="user",
        )
