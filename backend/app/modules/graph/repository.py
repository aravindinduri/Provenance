"""
app/modules/graph/repository.py — Data access layer for tenant supply graph edges.

CRITICAL TENANT ISOLATION:
Every query on supplier_relationships MUST be filtered by org_id.
Supplier relationships encode who-buys-from-whom and are strictly tenant-isolated.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.pagination import apply_cursor_to_query, encode_cursor
from app.modules.companies.models import Company
from app.modules.graph.models import SupplierRelationship


class GraphRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Suppliers (direct supply edges to tenant) ───────────────────────────

    async def get_supplier_by_id(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> tuple[SupplierRelationship, Company] | None:
        """Fetch a direct supplier relationship with joined Company."""
        stmt = (
            select(SupplierRelationship, Company)
            .join(Company, SupplierRelationship.from_company_id == Company.id)
            .where(
                SupplierRelationship.id == supplier_id,
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            return None
        return row[0], row[1]

    async def list_suppliers(
        self,
        *,
        org_id: uuid.UUID,
        category: str | None = None,
        criticality: int | None = None,
        tier: int | None = None,
        active_only: bool = True,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[SupplierRelationship, Company]], str | None, bool]:
        """List direct suppliers for an org with cursor pagination."""
        limit = min(max(1, limit), 100)
        stmt: Select = (
            select(SupplierRelationship, Company)
            .join(Company, SupplierRelationship.from_company_id == Company.id)
            .where(
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
                or_(
                    SupplierRelationship.to_org_id == org_id,
                    SupplierRelationship.relationship_type == "supplies_to",
                ),
            )
        )

        if active_only:
            stmt = stmt.where(SupplierRelationship.valid_to.is_(None))

        if category:
            stmt = stmt.where(SupplierRelationship.category == category)

        if criticality is not None:
            stmt = stmt.where(SupplierRelationship.criticality == criticality)

        if tier is not None:
            stmt = stmt.where(SupplierRelationship.tier == tier)

        stmt = apply_cursor_to_query(
            stmt,
            cursor=cursor,
            sort_column=SupplierRelationship.created_at,
            id_column=SupplierRelationship.id,
            is_datetime=True,
            descending=True,
        )

        stmt = stmt.order_by(
            SupplierRelationship.created_at.desc(),
            SupplierRelationship.id.desc(),
        ).limit(limit + 1)

        result = await self.db.execute(stmt)
        rows = list(result.all())

        has_more = len(rows) > limit
        if has_more:
            items = rows[:limit]
            last_rel, _ = items[-1]
            next_cursor = encode_cursor(last_rel.created_at, last_rel.id)
        else:
            items = rows
            next_cursor = None

        return items, next_cursor, has_more

    async def create_supplier(
        self,
        *,
        org_id: uuid.UUID,
        from_company_id: uuid.UUID,
        tier: int = 1,
        criticality: int = 3,
        annual_spend_usd: float | None = None,
        category: str | None = None,
        single_source: bool = False,
        lead_time_days: int | None = None,
        confidence: float = 1.0,
        source: str = "user_declared",
    ) -> SupplierRelationship:
        """Create a direct supplier edge to this organization."""
        rel = SupplierRelationship(
            org_id=org_id,
            from_company_id=from_company_id,
            to_org_id=org_id,
            relationship_type="supplies_to",
            tier=tier,
            criticality=criticality,
            annual_spend_usd=annual_spend_usd,
            category=category,
            single_source=single_source,
            lead_time_days=lead_time_days,
            confidence=confidence,
            source=source,
            valid_from=date.today(),
        )
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def update_supplier(
        self,
        *,
        supplier_id: uuid.UUID,
        org_id: uuid.UUID,
        **kwargs: Any,
    ) -> SupplierRelationship | None:
        """Update fields on a supplier relationship."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == supplier_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return None

        for k, v in kwargs.items():
            if v is not None and hasattr(rel, k):
                setattr(rel, k, v)

        await self.db.flush()
        return rel

    async def soft_delete_supplier(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> bool:
        """Soft-delete a supplier edge (sets valid_to and deleted_at)."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == supplier_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return False

        now = datetime.now()
        rel.valid_to = now.date()
        rel.deleted_at = now
        await self.db.flush()
        return True

    # ── Generic Graph Relationships ─────────────────────────────────────────

    async def get_relationship_by_id(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> tuple[SupplierRelationship, Company, Company | None] | None:
        """Fetch an edge with from_company and optional to_company."""
        from_comp = aliased(Company, name="from_comp")
        to_comp = aliased(Company, name="to_comp")

        stmt = (
            select(SupplierRelationship, from_comp, to_comp)
            .join(from_comp, SupplierRelationship.from_company_id == from_comp.id)
            .outerjoin(to_comp, SupplierRelationship.to_company_id == to_comp.id)
            .where(
                SupplierRelationship.id == rel_id,
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            return None
        return row[0], row[1], row[2]

    async def list_relationships(
        self,
        *,
        org_id: uuid.UUID,
        relationship_type: str | None = None,
        from_company_id: uuid.UUID | None = None,
        to_company_id: uuid.UUID | None = None,
        tier: int | None = None,
        active_only: bool = True,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[SupplierRelationship, Company, Company | None]], str | None, bool]:
        """List graph edges with cursor pagination."""
        limit = min(max(1, limit), 100)
        from_comp = aliased(Company, name="from_comp")
        to_comp = aliased(Company, name="to_comp")

        stmt: Select = (
            select(SupplierRelationship, from_comp, to_comp)
            .join(from_comp, SupplierRelationship.from_company_id == from_comp.id)
            .outerjoin(to_comp, SupplierRelationship.to_company_id == to_comp.id)
            .where(
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
            )
        )

        if active_only:
            stmt = stmt.where(SupplierRelationship.valid_to.is_(None))

        if relationship_type:
            stmt = stmt.where(SupplierRelationship.relationship_type == relationship_type)

        if from_company_id:
            stmt = stmt.where(SupplierRelationship.from_company_id == from_company_id)

        if to_company_id:
            stmt = stmt.where(SupplierRelationship.to_company_id == to_company_id)

        if tier is not None:
            stmt = stmt.where(SupplierRelationship.tier == tier)

        stmt = apply_cursor_to_query(
            stmt,
            cursor=cursor,
            sort_column=SupplierRelationship.created_at,
            id_column=SupplierRelationship.id,
            is_datetime=True,
            descending=True,
        )

        stmt = stmt.order_by(
            SupplierRelationship.created_at.desc(),
            SupplierRelationship.id.desc(),
        ).limit(limit + 1)

        result = await self.db.execute(stmt)
        rows = list(result.all())

        has_more = len(rows) > limit
        if has_more:
            items = rows[:limit]
            last_rel, _, _ = items[-1]
            next_cursor = encode_cursor(last_rel.created_at, last_rel.id)
        else:
            items = rows
            next_cursor = None

        return items, next_cursor, has_more

    async def create_relationship(
        self,
        *,
        org_id: uuid.UUID,
        from_company_id: uuid.UUID,
        to_company_id: uuid.UUID | None = None,
        to_org_id: uuid.UUID | None = None,
        relationship_type: str = "supplies_to",
        tier: int | None = None,
        criticality: int | None = None,
        annual_spend_usd: float | None = None,
        category: str | None = None,
        single_source: bool = False,
        lead_time_days: int | None = None,
        confidence: float = 1.0,
        source: str = "user_declared",
    ) -> SupplierRelationship:
        """Create a graph edge for an organization."""
        rel = SupplierRelationship(
            org_id=org_id,
            from_company_id=from_company_id,
            to_company_id=to_company_id,
            to_org_id=to_org_id,
            relationship_type=relationship_type,
            tier=tier,
            criticality=criticality,
            annual_spend_usd=annual_spend_usd,
            category=category,
            single_source=single_source,
            lead_time_days=lead_time_days,
            confidence=confidence,
            source=source,
            valid_from=date.today(),
        )
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def update_relationship(
        self,
        *,
        rel_id: uuid.UUID,
        org_id: uuid.UUID,
        **kwargs: Any,
    ) -> SupplierRelationship | None:
        """Update attributes on an edge."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == rel_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return None

        for k, v in kwargs.items():
            if v is not None and hasattr(rel, k):
                setattr(rel, k, v)

        await self.db.flush()
        return rel

    async def soft_delete_relationship(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> bool:
        """Soft-delete a relationship edge."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == rel_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return False

        now = datetime.now()
        rel.valid_to = now.date()
        rel.deleted_at = now
        await self.db.flush()
        return True
