"""
app/modules/items/repository.py — Data access layer for item catalog.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.items.models import Item


class ItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, item_id: uuid.UUID, org_id: uuid.UUID) -> Item | None:
        stmt = select(Item).where(
            Item.id == item_id,
            Item.org_id == org_id,
            Item.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, item_code: str, org_id: uuid.UUID) -> Item | None:
        stmt = select(Item).where(
            Item.item_code == item_code,
            Item.org_id == org_id,
            Item.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        org_id: uuid.UUID,
        *,
        q: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Item], int]:
        base = select(Item).where(Item.org_id == org_id, Item.deleted_at.is_(None))

        if q:
            pattern = f"%{q}%"
            base = base.where(
                or_(Item.name.ilike(pattern), Item.item_code.ilike(pattern))
            )
        if category is not None:
            base = base.where(Item.category == category)
        if is_active is not None:
            base = base.where(Item.is_active == is_active)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        items_stmt = base.order_by(Item.name).limit(limit).offset(offset)
        rows = (await self.db.execute(items_stmt)).scalars().all()
        return rows, total

    async def create(self, org_id: uuid.UUID, *, created_by: str | None = None, **kwargs) -> Item:
        item = Item(org_id=org_id, created_by=created_by, **kwargs)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update(self, item: Item, updates: dict, *, updated_by: str | None = None) -> Item:
        for key, value in updates.items():
            setattr(item, key, value)
        if updated_by:
            item.updated_by = updated_by
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def soft_delete(self, item: Item) -> None:
        from datetime import datetime, timezone
        item.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
