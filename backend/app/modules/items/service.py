"""
app/modules/items/service.py — Business logic for item catalog.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.items.models import Item
from app.modules.items.repository import ItemRepository
from app.modules.items.schemas import ItemCreate, ItemOut, ItemUpdate, PaginatedItems


class ItemNotFound(Exception):
    def __init__(self, item_id: uuid.UUID) -> None:
        super().__init__(f"Item {item_id} not found")
        self.item_id = item_id


class DuplicateItemCode(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(f"Item code '{code}' already exists in this organization")
        self.code = code


class ItemService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ItemRepository(db)

    async def list_items(
        self,
        org_id: uuid.UUID,
        *,
        q: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedItems:
        rows, total = await self.repo.list(
            org_id, q=q, category=category, is_active=is_active, limit=limit, offset=offset
        )
        return PaginatedItems(
            items=[ItemOut.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_item(self, item_id: uuid.UUID, org_id: uuid.UUID) -> Item:
        item = await self.repo.get_by_id(item_id, org_id)
        if not item:
            raise ItemNotFound(item_id)
        return item

    async def create_item(
        self, org_id: uuid.UUID, data: ItemCreate, *, created_by: str | None = None
    ) -> Item:
        existing = await self.repo.get_by_code(data.item_code, org_id)
        if existing:
            raise DuplicateItemCode(data.item_code)
        return await self.repo.create(
            org_id,
            created_by=created_by,
            item_code=data.item_code,
            name=data.name,
            description=data.description,
            category=data.category,
            unit_of_measure=data.unit_of_measure,
            default_unit_price=data.default_unit_price,
            currency=data.currency,
            preferred_supplier_id=data.preferred_supplier_id,
            lead_time_days=data.lead_time_days,
            min_order_qty=data.min_order_qty,
            is_active=data.is_active,
            metadata_=data.metadata,
        )

    async def update_item(
        self,
        item_id: uuid.UUID,
        org_id: uuid.UUID,
        data: ItemUpdate,
        *,
        updated_by: str | None = None,
    ) -> Item:
        item = await self.get_item(item_id, org_id)
        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or True}
        # map metadata field to ORM column name
        if "metadata" in updates:
            updates["metadata_"] = updates.pop("metadata")
        return await self.repo.update(item, updates, updated_by=updated_by)

    async def delete_item(self, item_id: uuid.UUID, org_id: uuid.UUID) -> None:
        item = await self.get_item(item_id, org_id)
        await self.repo.soft_delete(item)
