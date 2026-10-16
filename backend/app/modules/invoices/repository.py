"""
app/modules/invoices/repository.py — Database access layer for Invoices (spend_records).

RLS ENABLED. All queries filter by org_id.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.companies.models import Company
from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.spend.models import PurchaseOrder, SpendRecord


class InvoiceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_invoice_number(self, org_id: uuid.UUID) -> str:
        """
        Generate next sequential invoice number for this org.
        Format: INV-YYYY-NNNN
        """
        year = datetime.now(timezone.utc).year
        prefix = f"INV-{year}-"

        stmt = select(SpendRecord.invoice_number).where(
            SpendRecord.org_id == org_id,
            SpendRecord.invoice_number.ilike(f"{prefix}%"),
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().all()

        max_seq = 0
        pattern = re.compile(rf"^INV-{year}-(\d+)$")
        for num in existing:
            if not num:
                continue
            m = pattern.match(num.strip().upper())
            if m:
                try:
                    seq = int(m.group(1))
                    if seq > max_seq:
                        max_seq = seq
                except ValueError:
                    pass

        return f"{prefix}{max_seq + 1:04d}"

    async def create(self, invoice: SpendRecord) -> SpendRecord:
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def get_by_id(
        self, invoice_id: uuid.UUID, org_id: uuid.UUID
    ) -> SpendRecord | None:
        stmt = (
            select(SpendRecord)
            .options(
                selectinload(SpendRecord.company),
                selectinload(SpendRecord.purchase_order),
                selectinload(SpendRecord.goods_receipt),
            )
            .where(
                SpendRecord.id == invoice_id,
                SpendRecord.org_id == org_id,
                SpendRecord.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_number(
        self, invoice_number: str, org_id: uuid.UUID
    ) -> SpendRecord | None:
        stmt = (
            select(SpendRecord)
            .options(
                selectinload(SpendRecord.company),
                selectinload(SpendRecord.purchase_order),
                selectinload(SpendRecord.goods_receipt),
            )
            .where(
                SpendRecord.invoice_number.ilike(invoice_number.strip()),
                SpendRecord.org_id == org_id,
                SpendRecord.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_invoices(
        self,
        org_id: uuid.UUID,
        *,
        po_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        match_status: str | None = None,
        payment_status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SpendRecord], int]:
        filters: list[Any] = [
            SpendRecord.org_id == org_id,
            SpendRecord.deleted_at.is_(None),
        ]

        if po_id:
            filters.append(SpendRecord.po_id == po_id)
        if company_id:
            filters.append(SpendRecord.company_id == company_id)
        if match_status:
            filters.append(SpendRecord.match_status == match_status)
        if payment_status:
            filters.append(SpendRecord.payment_status == payment_status)
        if search:
            s = f"%{search.strip()}%"
            filters.append(
                or_(
                    SpendRecord.invoice_number.ilike(s),
                    SpendRecord.category.ilike(s),
                    SpendRecord.notes.ilike(s),
                )
            )

        count_stmt = select(func.count(SpendRecord.id)).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(SpendRecord)
            .options(
                selectinload(SpendRecord.company),
                selectinload(SpendRecord.purchase_order),
                selectinload(SpendRecord.goods_receipt),
            )
            .where(*filters)
            .order_by(SpendRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def get_unmatched(
        self, org_id: uuid.UUID | None = None
    ) -> list[SpendRecord]:
        """Fetch invoices that have linked POs and are pending matching."""
        filters = [
            SpendRecord.match_status == "unmatched",
            SpendRecord.po_id.isnot(None),
            SpendRecord.deleted_at.is_(None),
        ]
        if org_id:
            filters.append(SpendRecord.org_id == org_id)

        stmt = (
            select(SpendRecord)
            .options(
                selectinload(SpendRecord.purchase_order),
                selectinload(SpendRecord.goods_receipt),
            )
            .where(*filters)
            .order_by(SpendRecord.created_at.asc())
            .limit(100)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_stats(self, org_id: uuid.UUID) -> dict[str, Any]:
        """Compute live dynamic summary stats for invoices."""
        base_filters = [
            SpendRecord.org_id == org_id,
            SpendRecord.deleted_at.is_(None),
        ]

        stmt = select(
            func.count(SpendRecord.id).label("total_count"),
            func.coalesce(func.sum(SpendRecord.amount), 0).label("total_amount"),
            func.count(SpendRecord.id)
            .filter(SpendRecord.match_status == "matched_3way")
            .label("matched_3way_count"),
            func.count(SpendRecord.id)
            .filter(SpendRecord.match_status == "matched_2way")
            .label("matched_2way_count"),
            func.count(SpendRecord.id)
            .filter(SpendRecord.match_status == "exception")
            .label("exception_count"),
            func.count(SpendRecord.id)
            .filter(SpendRecord.match_status == "unmatched")
            .label("unmatched_count"),
            func.count(SpendRecord.id)
            .filter(SpendRecord.payment_status == "paid")
            .label("paid_count"),
            func.count(SpendRecord.id)
            .filter(SpendRecord.payment_status != "paid")
            .label("unpaid_count"),
            func.coalesce(
                func.sum(SpendRecord.amount).filter(
                    SpendRecord.payment_status == "paid"
                ),
                0,
            ).label("paid_amount"),
        ).where(*base_filters)

        row = (await self.db.execute(stmt)).one()
        return {
            "total_count": int(row.total_count or 0),
            "total_amount": float(row.total_amount or 0.0),
            "matched_3way_count": int(row.matched_3way_count or 0),
            "matched_2way_count": int(row.matched_2way_count or 0),
            "exception_count": int(row.exception_count or 0),
            "unmatched_count": int(row.unmatched_count or 0),
            "paid_count": int(row.paid_count or 0),
            "unpaid_count": int(row.unpaid_count or 0),
            "paid_amount": float(row.paid_amount or 0.0),
        }
