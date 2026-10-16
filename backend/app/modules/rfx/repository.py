"""
app/modules/rfx/repository.py — Data access for RFx sourcing events, invitations, and responses.

Deterministic sequence generation:
- Sourcing events: {TYPE}-{YEAR}-{sequence padded to 4} (e.g. RFQ-2026-0001, RFP-2026-0001)
- Supplier quotations: QUO-{YEAR}-{sequence padded to 4} (e.g. QUO-2026-0001)
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence as Seq
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.companies.models import Company
from app.modules.rfx.models import RFxEvent, RFxInvitation, RFxResponse


class RFxRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Number Generation ─────────────────────────────────────────────────────

    async def next_rfx_number(self, org_id: uuid.UUID, rfx_type: str = "rfq") -> str:
        """Generate next RFx number in format TYPE-YYYY-NNNN."""
        year = date.today().year
        prefix = f"{rfx_type.upper()}-{year}-"
        stmt = select(func.count()).where(
            RFxEvent.org_id == org_id,
            RFxEvent.rfx_number.like(f"{prefix}%"),
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return f"{prefix}{str(count + 1).zfill(4)}"

    async def next_response_number(self, org_id: uuid.UUID) -> str:
        """Generate next quotation response number in format QUO-YYYY-NNNN."""
        year = date.today().year
        prefix = f"QUO-{year}-"
        stmt = select(func.count()).where(
            RFxResponse.org_id == org_id,
            RFxResponse.response_number.like(f"{prefix}%"),
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return f"{prefix}{str(count + 1).zfill(4)}"

    # ── RFx Events CRUD ───────────────────────────────────────────────────────

    async def get_by_id(self, rfx_id: uuid.UUID, org_id: uuid.UUID) -> RFxEvent | None:
        stmt = (
            select(RFxEvent)
            .options(
                selectinload(RFxEvent.invitations).selectinload(RFxInvitation.supplier),
                selectinload(RFxEvent.responses).selectinload(RFxResponse.supplier),
                selectinload(RFxEvent.awarded_supplier),
            )
            .where(
                RFxEvent.id == rfx_id,
                RFxEvent.org_id == org_id,
                RFxEvent.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        org_id: uuid.UUID,
        *,
        status: str | None = None,
        rfx_type: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Seq[RFxEvent], int]:
        base = select(RFxEvent).where(
            RFxEvent.org_id == org_id,
            RFxEvent.deleted_at.is_(None),
        )
        if status:
            base = base.where(RFxEvent.status == status)
        if rfx_type:
            base = base.where(RFxEvent.rfx_type == rfx_type)
        if category:
            base = base.where(RFxEvent.category == category)

        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                base.options(
                    selectinload(RFxEvent.invitations).selectinload(RFxInvitation.supplier),
                    selectinload(RFxEvent.responses).selectinload(RFxResponse.supplier),
                    selectinload(RFxEvent.awarded_supplier),
                )
                .order_by(RFxEvent.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def create(
        self,
        org_id: uuid.UUID,
        *,
        rfx_number: str,
        rfx_type: str,
        title: str,
        description: str | None,
        material_request_id: uuid.UUID | None,
        category: str | None,
        evaluation_criteria: list[dict[str, Any]],
        submission_deadline: datetime | None,
        created_by: str | None,
    ) -> RFxEvent:
        rfx = RFxEvent(
            org_id=org_id,
            rfx_number=rfx_number,
            rfx_type=rfx_type,
            title=title,
            description=description,
            status="draft",
            material_request_id=material_request_id,
            category=category,
            evaluation_criteria=evaluation_criteria,
            submission_deadline=submission_deadline,
            created_by=created_by,
        )
        self.db.add(rfx)
        await self.db.flush()
        return rfx

    async def update(
        self,
        rfx: RFxEvent,
        updates: dict[str, Any],
        *,
        updated_by: str | None = None,
    ) -> RFxEvent:
        for k, v in updates.items():
            if hasattr(rfx, k):
                setattr(rfx, k, v)
        if updated_by:
            rfx.updated_by = updated_by
        self.db.add(rfx)
        await self.db.flush()
        return rfx

    async def update_status(self, rfx: RFxEvent, new_status: str, *, updated_by: str | None = None) -> RFxEvent:
        rfx.status = new_status
        if updated_by:
            rfx.updated_by = updated_by
        if new_status == "published" and not rfx.published_at:
            rfx.published_at = datetime.now(timezone.utc)
        self.db.add(rfx)
        await self.db.flush()
        return rfx

    # ── Invitations ───────────────────────────────────────────────────────────

    async def add_invitations(
        self,
        rfx: RFxEvent,
        supplier_ids: list[uuid.UUID],
        org_id: uuid.UUID,
        *,
        created_by: str | None = None,
    ) -> list[RFxInvitation]:
        stmt = select(RFxInvitation.supplier_id).where(
            RFxInvitation.rfx_event_id == rfx.id,
            RFxInvitation.deleted_at.is_(None),
        )
        existing_ids = set((await self.db.execute(stmt)).scalars().all())

        new_invites: list[RFxInvitation] = []
        for sup_id in supplier_ids:
            if sup_id not in existing_ids:
                inv = RFxInvitation(
                    org_id=org_id,
                    rfx_event_id=rfx.id,
                    supplier_id=sup_id,
                    status="invited",
                    created_by=created_by,
                )
                self.db.add(inv)
                new_invites.append(inv)
                existing_ids.add(sup_id)

        await self.db.flush()
        return new_invites

    async def get_invitation(
        self, rfx_event_id: uuid.UUID, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> RFxInvitation | None:
        stmt = select(RFxInvitation).where(
            RFxInvitation.rfx_event_id == rfx_event_id,
            RFxInvitation.supplier_id == supplier_id,
            RFxInvitation.org_id == org_id,
            RFxInvitation.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # ── Responses / Quotations ────────────────────────────────────────────────

    async def create_response(
        self,
        org_id: uuid.UUID,
        *,
        rfx_event_id: uuid.UUID,
        supplier_id: uuid.UUID,
        response_number: str,
        total_amount: float,
        currency: str,
        line_items: list[dict[str, Any]],
        validity_date: date | None = None,
        payment_terms: str | None = None,
        delivery_terms: str | None = None,
        attachments: list[Any] | None = None,
        source_document_id: uuid.UUID | None = None,
        created_by: str | None = None,
    ) -> RFxResponse:
        resp = RFxResponse(
            org_id=org_id,
            rfx_event_id=rfx_event_id,
            supplier_id=supplier_id,
            response_number=response_number,
            total_amount=total_amount,
            currency=currency,
            line_items=line_items,
            validity_date=validity_date,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            attachments=attachments or [],
            source_document_id=source_document_id,
            created_by=created_by,
        )
        self.db.add(resp)
        await self.db.flush()
        return resp

    async def get_response_by_id(self, response_id: uuid.UUID, org_id: uuid.UUID) -> RFxResponse | None:
        stmt = (
            select(RFxResponse)
            .options(selectinload(RFxResponse.supplier), selectinload(RFxResponse.rfx_event))
            .where(
                RFxResponse.id == response_id,
                RFxResponse.org_id == org_id,
                RFxResponse.deleted_at.is_(None),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_responses(
        self,
        org_id: uuid.UUID,
        *,
        rfx_event_id: uuid.UUID | None = None,
        supplier_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Seq[RFxResponse], int]:
        base = select(RFxResponse).where(
            RFxResponse.org_id == org_id,
            RFxResponse.deleted_at.is_(None),
        )
        if rfx_event_id:
            base = base.where(RFxResponse.rfx_event_id == rfx_event_id)
        if supplier_id:
            base = base.where(RFxResponse.supplier_id == supplier_id)

        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        rows = (
            await self.db.execute(
                base.options(selectinload(RFxResponse.supplier), selectinload(RFxResponse.rfx_event))
                .order_by(RFxResponse.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def update_response_scores(
        self,
        response: RFxResponse,
        scores: list[dict[str, Any]],
        *,
        updated_by: str | None = None,
    ) -> RFxResponse:
        response.evaluation_scores = scores
        if updated_by:
            response.updated_by = updated_by
        self.db.add(response)
        await self.db.flush()
        return response

    async def set_best_offer(self, rfx_event_id: uuid.UUID, best_response_id: uuid.UUID, org_id: uuid.UUID) -> None:
        # Clear best offer flags for all responses on this RFx
        stmt = select(RFxResponse).where(
            RFxResponse.rfx_event_id == rfx_event_id,
            RFxResponse.org_id == org_id,
        )
        resps = (await self.db.execute(stmt)).scalars().all()
        for r in resps:
            r.is_best_offer = (r.id == best_response_id)
            self.db.add(r)
        await self.db.flush()
