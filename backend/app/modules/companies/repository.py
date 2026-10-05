"""
app/modules/companies/repository.py — Data access layer for canonical companies.

The companies table is global reference data (cross-tenant).
No org_id is stored here, and no RLS is enabled on companies.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import apply_cursor_to_query, encode_cursor
from app.modules.companies.models import Company
from app.modules.companies.normalizer import normalize_company_name
from app.modules.graph.models import CompanyLocation


class CompanyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        """Fetch company by ID with identifiers and aliases loaded."""
        stmt = (
            select(Company)
            .options(
                selectinload(Company.identifiers),
                selectinload(Company.aliases),
            )
            .where(Company.id == company_id, Company.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_locations_for_company(
        self, company_id: uuid.UUID
    ) -> Sequence[CompanyLocation]:
        """Fetch active CompanyLocation records with linked Location for a company."""
        stmt = (
            select(CompanyLocation)
            .options(selectinload(CompanyLocation.location))
            .where(
                CompanyLocation.company_id == company_id,
                CompanyLocation.valid_to.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_exact_name(self, name: str) -> Company | None:
        """Find company by exact normalized name or legal name."""
        norm = normalize_company_name(name)
        stmt = (
            select(Company)
            .where(
                or_(Company.name_norm == norm, Company.legal_name == name),
                Company.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        q: str | None = None,
        country: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Company], str | None, bool]:
        """
        Cursor-paginated search over canonical companies.
        Stable under concurrent insert using (created_at DESC, id DESC).
        """
        limit = min(max(1, limit), 100)
        stmt: Select = select(Company).where(Company.deleted_at.is_(None))

        if q:
            norm = normalize_company_name(q)
            stmt = stmt.where(
                or_(
                    Company.legal_name.ilike(f"%{q}%"),
                    Company.name_norm.ilike(f"%{norm}%"),
                )
            )

        if country:
            stmt = stmt.where(Company.country == country.upper())

        # Apply cursor seeking before ordering
        stmt = apply_cursor_to_query(
            stmt,
            cursor=cursor,
            sort_column=Company.created_at,
            id_column=Company.id,
            is_datetime=True,
            descending=True,
        )

        stmt = stmt.order_by(Company.created_at.desc(), Company.id.desc())
        # Fetch limit + 1 to detect if next page exists
        stmt = stmt.limit(limit + 1)

        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        if has_more:
            items = rows[:limit]
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        else:
            items = rows
            next_cursor = None

        return items, next_cursor, has_more

    async def create(
        self,
        *,
        legal_name: str,
        country: str | None = None,
        jurisdiction: str | None = None,
        primary_domain: str | None = None,
        industry_codes: list[str] | None = None,
        data_source: str = "user",
    ) -> Company:
        """Create a new canonical company record."""
        norm = normalize_company_name(legal_name)
        company = Company(
            legal_name=legal_name,
            name_norm=norm,
            country=country.upper() if country else None,
            jurisdiction=jurisdiction,
            primary_domain=primary_domain,
            industry_codes=industry_codes or [],
            data_source=data_source,
        )
        self.db.add(company)
        await self.db.flush()
        return company
