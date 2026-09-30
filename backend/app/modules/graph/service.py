"""
app/modules/graph/service.py — Business logic for suppliers and relationships.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanySummaryOut
from app.modules.companies.service import CompanyNotFound, CompanyService
from app.modules.graph.repository import GraphRepository
from app.modules.graph.schemas import (
    RelationshipCreate,
    RelationshipOut,
    RelationshipUpdate,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)


def _to_float(val: object | None) -> float | None:
    return float(val) if val is not None else None


class SupplierNotFound(Exception):
    def __init__(self, supplier_id: uuid.UUID) -> None:
        super().__init__(f"Supplier {supplier_id} not found")
        self.supplier_id = supplier_id


class RelationshipNotFound(Exception):
    def __init__(self, rel_id: uuid.UUID) -> None:
        super().__init__(f"Relationship {rel_id} not found")
        self.rel_id = rel_id


class GraphService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GraphRepository(db)
        self.company_repo = CompanyRepository(db)
        self.company_svc = CompanyService(db)

    # ── Suppliers ───────────────────────────────────────────────────────────

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
    ) -> tuple[list[SupplierOut], str | None, bool]:
        rows, next_cursor, has_more = await self.repo.list_suppliers(
            org_id=org_id,
            category=category,
            criticality=criticality,
            tier=tier,
            active_only=active_only,
            cursor=cursor,
            limit=limit,
        )

        items = [
            SupplierOut(
                id=rel.id,
                org_id=rel.org_id,
                company_id=comp.id,
                company=CompanySummaryOut.model_validate(comp),
                relationship_type=rel.relationship_type,
                tier=rel.tier,
                criticality=rel.criticality,
                annual_spend_usd=_to_float(rel.annual_spend_usd),
                category=rel.category,
                single_source=rel.single_source,
                lead_time_days=rel.lead_time_days,
                confidence=float(rel.confidence),
                source=rel.source,
                valid_from=rel.valid_from,
                valid_to=rel.valid_to,
                created_at=rel.created_at,
                updated_at=rel.updated_at,
            )
            for rel, comp in rows
        ]

        return items, next_cursor, has_more

    async def get_supplier(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> SupplierOut:
        result = await self.repo.get_supplier_by_id(supplier_id, org_id)
        if not result:
            raise SupplierNotFound(supplier_id)

        rel, comp = result
        return SupplierOut(
            id=rel.id,
            org_id=rel.org_id,
            company_id=comp.id,
            company=CompanySummaryOut.model_validate(comp),
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def create_supplier(
        self, org_id: uuid.UUID, payload: SupplierCreate
    ) -> SupplierOut:
        # Resolve company
        if payload.company_id:
            company = await self.company_repo.get_by_id(payload.company_id)
            if not company:
                raise CompanyNotFound(payload.company_id)
        else:
            assert payload.legal_name is not None
            company = await self.company_svc.get_or_create_by_name(
                legal_name=payload.legal_name,
                country=payload.country,
                primary_domain=payload.primary_domain,
            )

        rel = await self.repo.create_supplier(
            org_id=org_id,
            from_company_id=company.id,
            tier=payload.tier,
            criticality=payload.criticality,
            annual_spend_usd=payload.annual_spend_usd,
            category=payload.category,
            single_source=payload.single_source,
            lead_time_days=payload.lead_time_days,
            confidence=payload.confidence,
            source=payload.source,
        )

        return SupplierOut(
            id=rel.id,
            org_id=rel.org_id,
            company_id=company.id,
            company=CompanySummaryOut.model_validate(company),
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def update_supplier(
        self,
        supplier_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: SupplierUpdate,
    ) -> SupplierOut:
        updates = payload.model_dump(exclude_unset=True)
        rel = await self.repo.update_supplier(
            supplier_id=supplier_id,
            org_id=org_id,
            **updates,
        )
        if not rel:
            raise SupplierNotFound(supplier_id)

        return await self.get_supplier(supplier_id, org_id)

    async def delete_supplier(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        deleted = await self.repo.soft_delete_supplier(supplier_id, org_id)
        if not deleted:
            raise SupplierNotFound(supplier_id)

    # ── Generic Relationships ───────────────────────────────────────────────

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
    ) -> tuple[list[RelationshipOut], str | None, bool]:
        rows, next_cursor, has_more = await self.repo.list_relationships(
            org_id=org_id,
            relationship_type=relationship_type,
            from_company_id=from_company_id,
            to_company_id=to_company_id,
            tier=tier,
            active_only=active_only,
            cursor=cursor,
            limit=limit,
        )

        items = [
            RelationshipOut(
                id=rel.id,
                org_id=rel.org_id,
                from_company_id=from_comp.id,
                from_company=CompanySummaryOut.model_validate(from_comp),
                to_company_id=to_comp.id if to_comp else None,
                to_company=CompanySummaryOut.model_validate(to_comp) if to_comp else None,
                to_org_id=rel.to_org_id,
                relationship_type=rel.relationship_type,
                tier=rel.tier,
                criticality=rel.criticality,
                annual_spend_usd=_to_float(rel.annual_spend_usd),
                category=rel.category,
                single_source=rel.single_source,
                lead_time_days=rel.lead_time_days,
                confidence=float(rel.confidence),
                source=rel.source,
                valid_from=rel.valid_from,
                valid_to=rel.valid_to,
                created_at=rel.created_at,
                updated_at=rel.updated_at,
            )
            for rel, from_comp, to_comp in rows
        ]

        return items, next_cursor, has_more

    async def get_relationship(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> RelationshipOut:
        result = await self.repo.get_relationship_by_id(rel_id, org_id)
        if not result:
            raise RelationshipNotFound(rel_id)

        rel, from_comp, to_comp = result
        return RelationshipOut(
            id=rel.id,
            org_id=rel.org_id,
            from_company_id=from_comp.id,
            from_company=CompanySummaryOut.model_validate(from_comp),
            to_company_id=to_comp.id if to_comp else None,
            to_company=CompanySummaryOut.model_validate(to_comp) if to_comp else None,
            to_org_id=rel.to_org_id,
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def create_relationship(
        self, org_id: uuid.UUID, payload: RelationshipCreate
    ) -> RelationshipOut:
        # Verify from_company exists
        from_comp = await self.company_repo.get_by_id(payload.from_company_id)
        if not from_comp:
            raise CompanyNotFound(payload.from_company_id)

        # Verify to_company if given
        to_comp = None
        if payload.to_company_id:
            to_comp = await self.company_repo.get_by_id(payload.to_company_id)
            if not to_comp:
                raise CompanyNotFound(payload.to_company_id)

        to_org_id = payload.to_org_id
        if not to_org_id and not payload.to_company_id:
            to_org_id = org_id

        rel = await self.repo.create_relationship(
            org_id=org_id,
            from_company_id=payload.from_company_id,
            to_company_id=payload.to_company_id,
            to_org_id=to_org_id,
            relationship_type=payload.relationship_type,
            tier=payload.tier,
            criticality=payload.criticality,
            annual_spend_usd=payload.annual_spend_usd,
            category=payload.category,
            single_source=payload.single_source,
            lead_time_days=payload.lead_time_days,
            confidence=payload.confidence,
            source=payload.source,
        )

        return RelationshipOut(
            id=rel.id,
            org_id=rel.org_id,
            from_company_id=from_comp.id,
            from_company=CompanySummaryOut.model_validate(from_comp),
            to_company_id=to_comp.id if to_comp else None,
            to_company=CompanySummaryOut.model_validate(to_comp) if to_comp else None,
            to_org_id=rel.to_org_id,
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def update_relationship(
        self,
        rel_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: RelationshipUpdate,
    ) -> RelationshipOut:
        updates = payload.model_dump(exclude_unset=True)
        rel = await self.repo.update_relationship(
            rel_id=rel_id,
            org_id=org_id,
            **updates,
        )
        if not rel:
            raise RelationshipNotFound(rel_id)

        return await self.get_relationship(rel_id, org_id)

    async def delete_relationship(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        deleted = await self.repo.soft_delete_relationship(rel_id, org_id)
        if not deleted:
            raise RelationshipNotFound(rel_id)
