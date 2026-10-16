"""
app/modules/rfx/service.py — Business logic for RFx sourcing events, quotations, and bid comparison.

Deterministic bid comparison engine:
- Price normalization using relative cost index: (min_price / price) * 100
- Delivery normalization using relative lead time: (min_lead / lead) * 100
- Weighted composite scoring across all defined evaluation criteria
- Clear explainability of best offer and ranking
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.models import Company
from app.modules.procurement.models import MaterialRequest
from app.modules.rfx.models import RFxEvent, RFxInvitation, RFxResponse
from app.modules.rfx.repository import RFxRepository
from app.modules.rfx.schemas import (
    BidComparisonItem,
    BidComparisonResult,
    PaginatedRFxEvents,
    PaginatedRFxResponses,
    RFxEventCreate,
    RFxEventOut,
    RFxEventUpdate,
    RFxInvitationOut,
    RFxResponseCreate,
    RFxResponseEvaluateRequest,
    RFxResponseOut,
)

logger = structlog.get_logger(__name__)

_VALID_RFX_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["published", "cancelled"],
    "published": ["q_and_a", "evaluation", "cancelled", "closed"],
    "q_and_a": ["evaluation", "cancelled", "closed"],
    "evaluation": ["negotiation", "awarded", "cancelled", "closed"],
    "negotiation": ["awarded", "evaluation", "cancelled", "closed"],
    "awarded": ["closed"],
    "cancelled": [],
    "closed": [],
}


class RFxNotFound(Exception):
    def __init__(self, rfx_id: uuid.UUID) -> None:
        super().__init__(f"RFx event {rfx_id} not found")
        self.rfx_id = rfx_id


class RFxResponseNotFound(Exception):
    def __init__(self, resp_id: uuid.UUID) -> None:
        super().__init__(f"Quotation response {resp_id} not found")
        self.resp_id = resp_id


class InvalidRFxStatusTransition(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition RFx event from '{current}' to '{target}'")


class RFxService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RFxRepository(db)

    # ── RFx Events ────────────────────────────────────────────────────────────

    async def list_rfx(
        self,
        org_id: uuid.UUID,
        *,
        status: str | None = None,
        rfx_type: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedRFxEvents:
        rows, total = await self.repo.list(
            org_id,
            status=status,
            rfx_type=rfx_type,
            category=category,
            limit=limit,
            offset=offset,
        )
        items: list[RFxEventOut] = []
        for r in rows:
            items.append(self._format_rfx_out(r))
        return PaginatedRFxEvents(items=items, total=total, limit=limit, offset=offset)

    async def get_rfx(self, rfx_id: uuid.UUID, org_id: uuid.UUID) -> RFxEvent:
        rfx = await self.repo.get_by_id(rfx_id, org_id)
        if not rfx:
            raise RFxNotFound(rfx_id)
        return rfx

    async def create_rfx(
        self,
        org_id: uuid.UUID,
        data: RFxEventCreate,
        *,
        user_id: str | None = None,
    ) -> RFxEvent:
        rfx_number = await self.repo.next_rfx_number(org_id, data.rfx_type)
        criteria_dicts = [c.model_dump() for c in data.evaluation_criteria]

        rfx = await self.repo.create(
            org_id,
            rfx_number=rfx_number,
            rfx_type=data.rfx_type,
            title=data.title,
            description=data.description,
            material_request_id=data.material_request_id,
            category=data.category,
            evaluation_criteria=criteria_dicts,
            submission_deadline=data.submission_deadline,
            created_by=user_id,
        )

        if data.supplier_ids:
            await self.repo.add_invitations(rfx, data.supplier_ids, org_id, created_by=user_id)

        await self.db.commit()
        await self.db.refresh(rfx)
        logger.info("rfx_event_created", rfx_number=rfx.rfx_number, org_id=str(org_id))
        return await self.get_rfx(rfx.id, org_id)

    async def update_rfx(
        self,
        rfx_id: uuid.UUID,
        org_id: uuid.UUID,
        data: RFxEventUpdate,
        *,
        user_id: str | None = None,
    ) -> RFxEvent:
        rfx = await self.get_rfx(rfx_id, org_id)
        if rfx.status not in ("draft",):
            raise InvalidRFxStatusTransition(rfx.status, "update")
        updates = data.model_dump(exclude_unset=True)
        if "evaluation_criteria" in updates and updates["evaluation_criteria"] is not None:
            updates["evaluation_criteria"] = [c.model_dump() for c in data.evaluation_criteria or []]

        rfx = await self.repo.update(rfx, updates, updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(rfx)
        return await self.get_rfx(rfx.id, org_id)

    async def publish_rfx(
        self, rfx_id: uuid.UUID, org_id: uuid.UUID, *, user_id: str | None = None
    ) -> RFxEvent:
        rfx = await self.get_rfx(rfx_id, org_id)
        self._assert_transition(rfx.status, "published")
        rfx = await self.repo.update_status(rfx, "published", updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(rfx)
        logger.info("rfx_event_published", rfx_number=rfx.rfx_number)
        return await self.get_rfx(rfx.id, org_id)

    async def close_rfx(
        self, rfx_id: uuid.UUID, org_id: uuid.UUID, *, user_id: str | None = None
    ) -> RFxEvent:
        rfx = await self.get_rfx(rfx_id, org_id)
        self._assert_transition(rfx.status, "closed")
        rfx = await self.repo.update_status(rfx, "closed", updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(rfx)
        return await self.get_rfx(rfx.id, org_id)

    async def cancel_rfx(
        self, rfx_id: uuid.UUID, org_id: uuid.UUID, *, user_id: str | None = None
    ) -> RFxEvent:
        rfx = await self.get_rfx(rfx_id, org_id)
        self._assert_transition(rfx.status, "cancelled")
        rfx = await self.repo.update_status(rfx, "cancelled", updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(rfx)
        return await self.get_rfx(rfx.id, org_id)

    async def invite_suppliers(
        self,
        rfx_id: uuid.UUID,
        org_id: uuid.UUID,
        supplier_ids: list[uuid.UUID],
        *,
        user_id: str | None = None,
    ) -> list[RFxInvitation]:
        rfx = await self.get_rfx(rfx_id, org_id)
        invs = await self.repo.add_invitations(rfx, supplier_ids, org_id, created_by=user_id)
        await self.db.commit()
        return invs

    # ── Supplier Quotations / Responses ───────────────────────────────────────

    async def create_response(
        self,
        org_id: uuid.UUID,
        data: RFxResponseCreate,
        *,
        user_id: str | None = None,
    ) -> RFxResponse:
        rfx = await self.get_rfx(data.rfx_event_id, org_id)
        response_number = await self.repo.next_response_number(org_id)

        line_items_data = [li.model_dump() for li in data.line_items]
        total_amount = data.total_amount
        if total_amount is None:
            total_amount = sum(li["qty"] * li["unit_price"] for li in line_items_data)

        resp = await self.repo.create_response(
            org_id,
            rfx_event_id=rfx.id,
            supplier_id=data.supplier_id,
            response_number=response_number,
            total_amount=total_amount,
            currency=data.currency,
            line_items=line_items_data,
            validity_date=data.validity_date,
            payment_terms=data.payment_terms,
            delivery_terms=data.delivery_terms,
            attachments=data.attachments,
            source_document_id=data.source_document_id,
            created_by=user_id,
        )

        # Update invitation status if supplier was invited
        inv = await self.repo.get_invitation(rfx.id, data.supplier_id, org_id)
        if inv:
            inv.status = "responded"
            inv.responded_at = datetime.now(timezone.utc)
            self.db.add(inv)

        # Advance RFx to evaluation status if in published or q_and_a
        if rfx.status in ("published", "q_and_a"):
            rfx.status = "evaluation"
            self.db.add(rfx)

        await self.db.commit()
        await self.db.refresh(resp)
        logger.info("rfx_response_created", response_number=resp.response_number, rfx_number=rfx.rfx_number)
        return resp

    async def get_response(self, response_id: uuid.UUID, org_id: uuid.UUID) -> RFxResponse:
        resp = await self.repo.get_response_by_id(response_id, org_id)
        if not resp:
            raise RFxResponseNotFound(response_id)
        return resp

    async def list_responses(
        self,
        org_id: uuid.UUID,
        *,
        rfx_event_id: uuid.UUID | None = None,
        supplier_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedRFxResponses:
        rows, total = await self.repo.list_responses(
            org_id, rfx_event_id=rfx_event_id, supplier_id=supplier_id, limit=limit, offset=offset
        )
        items = [self._format_response_out(r) for r in rows]
        return PaginatedRFxResponses(items=items, total=total, limit=limit, offset=offset)

    async def evaluate_response(
        self,
        response_id: uuid.UUID,
        org_id: uuid.UUID,
        data: RFxResponseEvaluateRequest,
        *,
        user_id: str | None = None,
    ) -> RFxResponse:
        resp = await self.get_response(response_id, org_id)
        scores_data = [s.model_dump() for s in data.scores]
        resp = await self.repo.update_response_scores(resp, scores_data, updated_by=user_id)
        await self.db.commit()
        await self.db.refresh(resp)
        return resp

    # ── Deterministic Bid Comparison Engine ───────────────────────────────────

    async def compare_bids(self, rfx_id: uuid.UUID, org_id: uuid.UUID) -> BidComparisonResult:
        rfx = await self.get_rfx(rfx_id, org_id)
        responses, _ = await self.repo.list_responses(org_id, rfx_event_id=rfx.id, limit=100)

        if not responses:
            return BidComparisonResult(
                rfx_id=rfx.id,
                rfx_number=rfx.rfx_number,
                rfx_type=rfx.rfx_type,
                title=rfx.title,
                status=rfx.status,
                criteria=rfx.evaluation_criteria,
                bids=[],
                recommendation_summary="No quotations received yet for this sourcing event.",
            )

        # Compute price min/max
        prices = [float(r.total_amount) for r in responses if float(r.total_amount) > 0]
        min_price = min(prices) if prices else 1.0

        # Extract lead times
        lead_times: list[int] = []
        for r in responses:
            leads = [
                int(li.get("lead_time_days"))
                for li in (r.line_items or [])
                if li.get("lead_time_days") is not None
            ]
            if leads:
                lead_times.append(min(leads))
        min_lead_time = min(lead_times) if lead_times else 14

        # Compute weights map
        criteria_list = rfx.evaluation_criteria or [
            {"criterion": "Price", "weight": 40.0},
            {"criterion": "Quality", "weight": 25.0},
            {"criterion": "Delivery", "weight": 20.0},
            {"criterion": "Risk", "weight": 15.0},
        ]
        total_weight = sum(float(c.get("weight", 0)) for c in criteria_list) or 100.0

        # Score each bid
        comparison_items: list[BidComparisonItem] = []
        for resp in responses:
            price = float(resp.total_amount)
            # Relative price score: 100 * (min_price / price)
            norm_price_score = round((min_price / price) * 100.0, 2) if price > 0 else 0.0

            # Lead time calculation
            leads = [
                int(li.get("lead_time_days"))
                for li in (resp.line_items or [])
                if li.get("lead_time_days") is not None
            ]
            avg_lead = round(sum(leads) / len(leads)) if leads else None
            # Lead time score: 100 * (min_lead_time / lead_time)
            lead_score = (
                round((min_lead_time / avg_lead) * 100.0, 2)
                if avg_lead and avg_lead > 0
                else 80.0
            )

            # Manual evaluation scores mapping
            manual_scores: dict[str, float] = {}
            for sc in resp.evaluation_scores or []:
                if "criterion" in sc and "score" in sc:
                    manual_scores[sc["criterion"].lower()] = float(sc["score"])

            # Compute scores per criterion
            criteria_scores: dict[str, float] = {}
            weighted_sum = 0.0

            for crit in criteria_list:
                name = crit.get("criterion", "")
                name_lower = name.lower()
                weight = float(crit.get("weight", 0))

                if name_lower in manual_scores:
                    crit_score = manual_scores[name_lower]
                elif "price" in name_lower or "cost" in name_lower:
                    crit_score = norm_price_score
                elif "delivery" in name_lower or "lead" in name_lower:
                    crit_score = lead_score
                elif "quality" in name_lower:
                    crit_score = 85.0  # default baseline if unscored
                elif "risk" in name_lower:
                    crit_score = 80.0  # default baseline if unscored
                else:
                    crit_score = 75.0

                criteria_scores[name] = round(crit_score, 2)
                weighted_sum += crit_score * weight

            composite_score = round(weighted_sum / total_weight, 2)

            sup_name = resp.supplier.legal_name if resp.supplier else "Unknown Supplier"
            sup_country = resp.supplier.country if resp.supplier else None

            comparison_items.append(
                BidComparisonItem(
                    response_id=resp.id,
                    response_number=resp.response_number,
                    supplier_id=resp.supplier_id,
                    supplier_name=sup_name,
                    supplier_country=sup_country,
                    total_amount=price,
                    currency=resp.currency,
                    average_lead_time_days=avg_lead,
                    line_items=resp.line_items or [],
                    criteria_scores=criteria_scores,
                    normalized_price_score=norm_price_score,
                    composite_score=composite_score,
                    is_best_offer=resp.is_best_offer,
                    price_rank=1,
                    overall_rank=1,
                    payment_terms=resp.payment_terms,
                    delivery_terms=resp.delivery_terms,
                )
            )

        # Rank by price (lowest is rank 1)
        sorted_by_price = sorted(comparison_items, key=lambda x: x.total_amount)
        for idx, item in enumerate(sorted_by_price):
            item.price_rank = idx + 1

        # Rank by composite score (highest is rank 1)
        sorted_by_score = sorted(comparison_items, key=lambda x: x.composite_score, reverse=True)
        for idx, item in enumerate(sorted_by_score):
            item.overall_rank = idx + 1

        # Mark top composite rank as best offer recommendation
        best_bid = sorted_by_score[0] if sorted_by_score else None
        if best_bid:
            await self.repo.set_best_offer(rfx.id, best_bid.response_id, org_id)
            await self.db.commit()
            best_bid.is_best_offer = True

        recommendation = (
            f"Recommended award to {best_bid.supplier_name} ({best_bid.response_number}) "
            f"with overall score of {best_bid.composite_score}/100 and total amount of "
            f"{best_bid.currency} {best_bid.total_amount:,.2f}."
            if best_bid
            else "No eligible bids found."
        )

        return BidComparisonResult(
            rfx_id=rfx.id,
            rfx_number=rfx.rfx_number,
            rfx_type=rfx.rfx_type,
            title=rfx.title,
            status=rfx.status,
            criteria=criteria_list,
            bids=sorted_by_score,
            recommended_response_id=best_bid.response_id if best_bid else None,
            recommended_supplier_id=best_bid.supplier_id if best_bid else None,
            recommended_supplier_name=best_bid.supplier_name if best_bid else None,
            recommendation_summary=recommendation,
        )

    # ── Awarding ──────────────────────────────────────────────────────────────

    async def award_rfx(
        self,
        rfx_id: uuid.UUID,
        org_id: uuid.UUID,
        response_id: uuid.UUID,
        *,
        user_id: str | None = None,
        notes: str | None = None,
    ) -> RFxEvent:
        rfx = await self.get_rfx(rfx_id, org_id)
        if rfx.status not in ("evaluation", "negotiation", "published"):
            raise InvalidRFxStatusTransition(rfx.status, "awarded")

        resp = await self.get_response(response_id, org_id)
        if resp.rfx_event_id != rfx.id:
            raise ValueError(f"Response {response_id} does not belong to RFx {rfx_id}")

        # Update RFx status and winner
        rfx.status = "awarded"
        rfx.awarded_at = datetime.now(timezone.utc)
        rfx.awarded_supplier_id = resp.supplier_id
        rfx.updated_by = user_id
        self.db.add(rfx)

        # Mark best offer
        await self.repo.set_best_offer(rfx.id, resp.id, org_id)

        # Update invitations: awarded vs rejected
        for inv in rfx.invitations:
            if inv.supplier_id == resp.supplier_id:
                inv.status = "awarded"
            else:
                inv.status = "rejected"
            self.db.add(inv)

        await self.db.commit()
        await self.db.refresh(rfx)
        logger.info(
            "rfx_event_awarded",
            rfx_number=rfx.rfx_number,
            awarded_supplier=str(resp.supplier_id),
            response_number=resp.response_number,
        )
        return await self.get_rfx(rfx.id, org_id)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_transition(self, current: str, target: str) -> None:
        if target not in _VALID_RFX_TRANSITIONS.get(current, []):
            raise InvalidRFxStatusTransition(current, target)

    def _format_rfx_out(self, rfx: RFxEvent) -> RFxEventOut:
        invitations = [
            RFxInvitationOut(
                id=inv.id,
                rfx_event_id=inv.rfx_event_id,
                supplier_id=inv.supplier_id,
                status=inv.status,
                invited_at=inv.invited_at,
                responded_at=inv.responded_at,
                supplier_legal_name=inv.supplier.legal_name if inv.supplier else None,
                supplier_country=inv.supplier.country if inv.supplier else None,
            )
            for inv in (rfx.invitations or [])
        ]
        responses = [self._format_response_out(resp) for resp in (rfx.responses or [])]

        return RFxEventOut(
            id=rfx.id,
            org_id=rfx.org_id,
            rfx_number=rfx.rfx_number,
            rfx_type=rfx.rfx_type,
            title=rfx.title,
            description=rfx.description,
            status=rfx.status,
            material_request_id=rfx.material_request_id,
            category=rfx.category,
            evaluation_criteria=rfx.evaluation_criteria or [],
            published_at=rfx.published_at,
            submission_deadline=rfx.submission_deadline,
            awarded_at=rfx.awarded_at,
            awarded_supplier_id=rfx.awarded_supplier_id,
            awarded_supplier_name=rfx.awarded_supplier.legal_name if rfx.awarded_supplier else None,
            created_by=rfx.created_by,
            created_at=rfx.created_at,
            updated_at=rfx.updated_at,
            invitations=invitations,
            responses=responses,
            total_invitations=len(invitations),
            total_responses=len(responses),
        )

    def _format_response_out(self, resp: RFxResponse) -> RFxResponseOut:
        return RFxResponseOut(
            id=resp.id,
            rfx_event_id=resp.rfx_event_id,
            supplier_id=resp.supplier_id,
            response_number=resp.response_number,
            total_amount=float(resp.total_amount),
            currency=resp.currency,
            line_items=resp.line_items or [],
            evaluation_scores=resp.evaluation_scores,
            validity_date=resp.validity_date,
            payment_terms=resp.payment_terms,
            delivery_terms=resp.delivery_terms,
            submitted_at=resp.submitted_at,
            is_best_offer=resp.is_best_offer,
            source_document_id=resp.source_document_id,
            supplier_legal_name=resp.supplier.legal_name if resp.supplier else None,
            supplier_country=resp.supplier.country if resp.supplier else None,
        )
