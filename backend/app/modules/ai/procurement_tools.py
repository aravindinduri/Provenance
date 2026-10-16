"""
app/modules/ai/procurement_tools.py — Phase 1 agent tools.

Tools registered here:
  - create_material_request   Create MR from NL description + items list
  - approve_document          Approve or reject a document via its workflow

These are called from the investigation agent when procurement intent is detected.
All writes go to real DB tables; no mock data is generated.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approvals.service import ApprovalService, WorkflowNotFound, NotPendingStep
from app.modules.procurement.schemas import MaterialRequestCreate, MRLineItemCreate
from app.modules.procurement.service import ProcurementService, MRNotFound, InvalidStatusTransition

logger = structlog.get_logger(__name__)


class ProcurementToolError(Exception):
    pass


async def tool_create_material_request(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None,
    title: str,
    items: list[dict[str, Any]],
    required_by: str | None = None,
    priority: str = "medium",
    department: str | None = None,
    justification: str | None = None,
    currency: str | None = None,
    auto_submit: bool = False,
) -> dict[str, Any]:
    """
    Create a Material Request (optionally submit for approval immediately).

    items: list of {description, quantity, unit_of_measure?, estimated_unit_price?, currency?}
    required_by: ISO date string (YYYY-MM-DD), optional
    auto_submit: if True, submit to approval workflow right after creation
    """
    from datetime import date

    required_by_date = None
    if required_by:
        try:
            required_by_date = date.fromisoformat(required_by)
        except ValueError:
            logger.warning("procurement_tool_invalid_date", required_by=required_by)

    line_items = [
        MRLineItemCreate(
            description=li.get("description", ""),
            quantity=float(li.get("quantity", 1)),
            unit_of_measure=li.get("unit_of_measure"),
            estimated_unit_price=li.get("estimated_unit_price"),
            currency=li.get("currency", currency),
            item_id=uuid.UUID(li["item_id"]) if li.get("item_id") else None,
            preferred_supplier_id=uuid.UUID(li["preferred_supplier_id"]) if li.get("preferred_supplier_id") else None,
        )
        for li in items
    ]

    svc = ProcurementService(db)
    data = MaterialRequestCreate(
        title=title,
        required_by_date=required_by_date,
        priority=priority,  # type: ignore[arg-type]
        department=department,
        justification=justification,
        currency=currency,
        line_items=line_items,
    )
    mr = await svc.create_mr(org_id, data, user_id=user_id)

    result: dict[str, Any] = {
        "action": "create_material_request",
        "mr_number": mr.mr_number,
        "mr_id": str(mr.id),
        "status": mr.status,
        "title": mr.title,
        "total_estimated_amount": float(mr.total_estimated_amount or 0),
        "currency": mr.currency,
        "line_item_count": len(mr.line_items or []),
    }

    if auto_submit:
        try:
            mr = await svc.submit_mr(mr.id, org_id, user_id=user_id)
            result["status"] = mr.status
            result["submitted"] = True
        except InvalidStatusTransition as exc:
            result["submit_error"] = str(exc)

    logger.info("procurement_tool_mr_created", mr_number=mr.mr_number, org_id=str(org_id))
    return result


async def tool_approve_document(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None,
    document_type: str,
    document_id: str,
    action: str,
    comments: str | None = None,
) -> dict[str, Any]:
    """
    Approve or reject a document by finding its active approval workflow.

    document_type: material_request | purchase_order | invoice
    document_id: UUID string
    action: approve | reject
    """
    if action not in ("approve", "reject"):
        raise ProcurementToolError(f"Invalid action '{action}'. Must be 'approve' or 'reject'.")

    doc_uuid = uuid.UUID(document_id)
    svc = ApprovalService(db)
    wf = await svc.get_workflow_for_document(org_id, document_type, doc_uuid)
    if not wf:
        raise ProcurementToolError(
            f"No active approval workflow found for {document_type} {document_id}."
        )

    try:
        wf = await svc.decide(
            workflow_id=wf.id,
            org_id=org_id,
            action=action,
            user_id=user_id,
            comments=comments,
        )
    except WorkflowNotFound:
        raise ProcurementToolError(f"Workflow {wf.id} not found.")
    except NotPendingStep as exc:
        raise ProcurementToolError(str(exc))

    logger.info(
        "procurement_tool_approval_decided",
        document_type=document_type,
        document_id=document_id,
        action=action,
        workflow_status=wf.status,
    )

    return {
        "action": "approve_document",
        "document_type": document_type,
        "document_id": document_id,
        "decision": action,
        "workflow_id": str(wf.id),
        "workflow_status": wf.status,
        "step": wf.current_step,
        "comments": comments,
    }


# ── Phase 2 Tools: Sourcing & Bid Comparison ──────────────────────────────────

async def tool_create_rfx(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None,
    title: str,
    rfx_type: str = "rfq",
    description: str | None = None,
    material_request_id: str | None = None,
    supplier_ids: list[str] | None = None,
    criteria: list[dict[str, Any]] | None = None,
    deadline_days: int = 14,
    category: str | None = None,
    auto_publish: bool = True,
) -> dict[str, Any]:
    """
    Create an RFx sourcing event (optionally publish and invite suppliers).
    """
    from datetime import datetime, timedelta, timezone
    from app.modules.rfx.schemas import EvaluationCriterion, RFxEventCreate
    from app.modules.rfx.service import RFxService

    mr_uuid = uuid.UUID(material_request_id) if material_request_id else None
    sup_uuids = [uuid.UUID(s) for s in supplier_ids] if supplier_ids else []

    eval_criteria: list[EvaluationCriterion] = []
    if criteria:
        for c in criteria:
            eval_criteria.append(
                EvaluationCriterion(
                    criterion=c.get("criterion", "Quality"),
                    weight=float(c.get("weight", 25.0)),
                    description=c.get("description"),
                )
            )
    else:
        eval_criteria = [
            EvaluationCriterion(criterion="Price", weight=40.0, description="Cost competitiveness"),
            EvaluationCriterion(criterion="Quality", weight=25.0, description="Specifications compliance"),
            EvaluationCriterion(criterion="Delivery", weight=20.0, description="Fulfillment lead time"),
            EvaluationCriterion(criterion="Risk", weight=15.0, description="Supplier risk assessment rating"),
        ]

    deadline = datetime.now(timezone.utc) + timedelta(days=deadline_days)
    svc = RFxService(db)
    data = RFxEventCreate(
        rfx_type=rfx_type,  # type: ignore[arg-type]
        title=title,
        description=description,
        material_request_id=mr_uuid,
        category=category,
        evaluation_criteria=eval_criteria,
        submission_deadline=deadline,
        supplier_ids=sup_uuids,
    )
    rfx = await svc.create_rfx(org_id, data, user_id=user_id)

    if auto_publish:
        try:
            rfx = await svc.publish_rfx(rfx.id, org_id, user_id=user_id)
        except Exception as exc:
            logger.warning("tool_create_rfx_publish_failed", error=str(exc))

    return {
        "action": "create_rfx",
        "rfx_id": str(rfx.id),
        "rfx_number": rfx.rfx_number,
        "rfx_type": rfx.rfx_type,
        "title": rfx.title,
        "status": rfx.status,
        "submission_deadline": rfx.submission_deadline.isoformat() if rfx.submission_deadline else None,
        "invited_supplier_count": len(rfx.invitations or []),
        "criteria_count": len(rfx.evaluation_criteria or []),
    }


async def tool_compare_quotations(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None = None,
    rfx_id: str,
) -> dict[str, Any]:
    """
    Run deterministic bid comparison on all supplier quotations for an RFx event.
    """
    from app.modules.rfx.models import RFxEvent
    from app.modules.rfx.service import RFxNotFound, RFxService

    svc = RFxService(db)

    # Allow looking up by UUID string or RFx number (e.g. "RFQ-2026-0001")
    target_uuid: uuid.UUID | None = None
    try:
        target_uuid = uuid.UUID(rfx_id)
    except ValueError:
        stmt = select(RFxEvent.id).where(
            RFxEvent.org_id == org_id,
            RFxEvent.rfx_number.ilike(rfx_id.strip()),
            RFxEvent.deleted_at.is_(None),
        )
        target_uuid = (await db.execute(stmt)).scalar_one_or_none()

    if not target_uuid:
        raise ProcurementToolError(f"RFx event '{rfx_id}' not found.")

    try:
        result = await svc.compare_bids(target_uuid, org_id)
    except RFxNotFound:
        raise ProcurementToolError(f"RFx event '{rfx_id}' not found.")

    return {
        "action": "compare_quotations",
        "rfx_id": str(result.rfx_id),
        "rfx_number": result.rfx_number,
        "rfx_type": result.rfx_type,
        "title": result.title,
        "status": result.status,
        "total_bids": len(result.bids),
        "recommended_bid_id": str(result.recommended_response_id) if result.recommended_response_id else None,
        "recommended_supplier_id": str(result.recommended_supplier_id) if result.recommended_supplier_id else None,
        "recommended_supplier_name": result.recommended_supplier_name,
        "recommendation_summary": result.recommendation_summary,
        "bids": [b.model_dump() for b in result.bids],
    }


# ── Phase 3 Tools: Order-to-Receipt ───────────────────────────────────────────

async def tool_create_purchase_order(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None,
    supplier_id: str | None = None,
    supplier_name: str | None = None,
    line_items: list[dict[str, Any]],
    rfx_response_id: str | None = None,
    rfx_event_id: str | None = None,
    material_request_id: str | None = None,
    payment_terms: str = "Net 30",
    delivery_terms: str = "FOB Destination",
    expected_delivery_date: str | None = None,
    delivery_address: dict[str, Any] | None = None,
    notes: str | None = None,
    auto_submit: bool = True,
) -> dict[str, Any]:
    """
    Create a Purchase Order (and optionally route for DoA approval).
    """
    from datetime import date
    from app.modules.companies.models import Company
    from app.modules.purchase_orders.schemas import POLineItemCreate, PurchaseOrderCreate
    from app.modules.purchase_orders.service import PurchaseOrderService

    # Resolve supplier
    vendor_uuid: uuid.UUID | None = None
    resolved_supplier_name = supplier_name
    if supplier_id:
        try:
            vendor_uuid = uuid.UUID(supplier_id)
        except ValueError:
            pass

    if not vendor_uuid and supplier_name:
        stmt = (
            select(Company)
            .where(
                Company.legal_name.ilike(f"%{supplier_name.strip()}%"),
                Company.deleted_at.is_(None),
            )
            .limit(1)
        )
        found = (await db.execute(stmt)).scalar_one_or_none()
        if found:
            vendor_uuid = found.id
            resolved_supplier_name = found.legal_name

    if not vendor_uuid:
        # Fallback to the first available company in master
        stmt = (
            select(Company)
            .where(Company.deleted_at.is_(None))
            .order_by(Company.legal_name.asc())
            .limit(1)
        )
        first_comp = (await db.execute(stmt)).scalar_one_or_none()
        if first_comp:
            vendor_uuid = first_comp.id
            resolved_supplier_name = first_comp.legal_name
        else:
            raise ProcurementToolError("No supplier found or provided to assign purchase order.")

    # Parse delivery date
    delivery_date = None
    if expected_delivery_date:
        try:
            delivery_date = date.fromisoformat(expected_delivery_date)
        except ValueError:
            logger.warning("invalid_expected_delivery_date", date_str=expected_delivery_date)

    mr_uuid = uuid.UUID(material_request_id) if material_request_id else None
    rfx_uuid = uuid.UUID(rfx_event_id) if rfx_event_id else None
    resp_uuid = uuid.UUID(rfx_response_id) if rfx_response_id else None

    po_lines: list[POLineItemCreate] = []
    for li in line_items:
        po_lines.append(
            POLineItemCreate(
                item_id=uuid.UUID(li["item_id"]) if li.get("item_id") else None,
                item_code=li.get("item_code"),
                description=li.get("description", "Material Supply"),
                quantity=float(li.get("quantity", 1)),
                unit_of_measure=li.get("unit_of_measure", "each"),
                unit_price=float(li.get("unit_price", 0.0)),
                total_price=float(li["total_price"]) if li.get("total_price") is not None else None,
            )
        )

    if not po_lines:
        po_lines.append(
            POLineItemCreate(
                description="Materials per requisition specifications",
                quantity=1.0,
                unit_price=1000.0,
                unit_of_measure="each",
            )
        )

    po_data = PurchaseOrderCreate(
        company_id=vendor_uuid,
        material_request_id=mr_uuid,
        rfx_event_id=rfx_uuid,
        rfx_response_id=resp_uuid,
        order_date=date.today(),
        expected_delivery_date=delivery_date,
        currency="USD",
        line_items=po_lines,
        delivery_address=delivery_address,
        payment_terms=payment_terms,
        delivery_terms=delivery_terms,
        notes=notes,
    )

    svc = PurchaseOrderService(db)
    po = await svc.create_po(org_id, po_data, user_id=user_id)

    if auto_submit:
        try:
            po = await svc.submit_po(po.id, org_id, user_id=user_id)
        except Exception as exc:
            logger.warning("tool_create_po_submit_failed", error=str(exc))

    return {
        "action": "create_purchase_order",
        "po_id": str(po.id),
        "po_number": po.po_number,
        "company_id": str(po.company_id) if po.company_id else None,
        "company_name": resolved_supplier_name or po.company_name,
        "total_amount": float(po.total_amount),
        "currency": po.currency,
        "status": po.status,
        "item_count": len(po.line_items),
        "payment_terms": po.payment_terms,
        "delivery_terms": po.delivery_terms,
        "expected_delivery_date": po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
    }


async def tool_record_goods_receipt(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None,
    purchase_order_id: str,
    items_received: list[dict[str, Any]] | None = None,
    received_date: str | None = None,
    delivery_note_ref: str | None = None,
    carrier: str | None = None,
    notes: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any]:
    """
    Record a Goods Receipt Note against a purchase order.
    """
    from datetime import date
    from app.modules.goods_receipts.schemas import GoodsReceiptCreate, GRNLineItemInput
    from app.modules.goods_receipts.service import GoodsReceiptService
    from app.modules.purchase_orders.service import PurchaseOrderService
    from app.modules.spend.models import PurchaseOrder

    # Resolve PO
    target_po_uuid: uuid.UUID | None = None
    try:
        target_po_uuid = uuid.UUID(purchase_order_id)
    except ValueError:
        # Search by po_number or take latest active PO
        stmt = select(PurchaseOrder.id).where(
            PurchaseOrder.org_id == org_id,
            PurchaseOrder.po_number.ilike(purchase_order_id.strip()),
            PurchaseOrder.deleted_at.is_(None),
        )
        target_po_uuid = (await db.execute(stmt)).scalar_one_or_none()

    if not target_po_uuid:
        # Check if user meant latest approved/sent PO
        stmt = (
            select(PurchaseOrder.id)
            .where(
                PurchaseOrder.org_id == org_id,
                PurchaseOrder.status.in_(["approved", "sent", "acknowledged", "partially_received"]),
                PurchaseOrder.deleted_at.is_(None),
            )
            .order_by(PurchaseOrder.created_at.desc())
            .limit(1)
        )
        target_po_uuid = (await db.execute(stmt)).scalar_one_or_none()

    if not target_po_uuid:
        raise ProcurementToolError(f"Purchase order '{purchase_order_id}' not found or not in a receivable state.")

    po_svc = PurchaseOrderService(db)
    po = await po_svc.get_po(target_po_uuid, org_id)

    # Build line items
    grn_items: list[GRNLineItemInput] = []
    if items_received:
        for it in items_received:
            grn_items.append(
                GRNLineItemInput(
                    po_line_index=int(it.get("po_line_index", 0)),
                    item_id=uuid.UUID(it["item_id"]) if it.get("item_id") else None,
                    item_code=it.get("item_code"),
                    description=it.get("description", "Supplied Item"),
                    qty_received=float(it.get("qty_received", 1.0)),
                    qty_rejected=float(it.get("qty_rejected", 0.0)),
                    unit_of_measure=it.get("unit_of_measure", "each"),
                    inspection_notes=it.get("inspection_notes"),
                )
            )
    else:
        # Automatically fulfill all pending PO lines 100%
        for idx, po_item in enumerate(po.line_items):
            ordered = float(po_item.get("quantity", 1.0))
            already_rec = float(po_item.get("qty_received", 0.0))
            pending = max(0.0, ordered - already_rec)
            qty_to_receive = pending if pending > 0 else ordered
            grn_items.append(
                GRNLineItemInput(
                    po_line_index=idx,
                    item_id=uuid.UUID(po_item["item_id"]) if po_item.get("item_id") else None,
                    item_code=po_item.get("item_code"),
                    description=po_item.get("description", "Supplied Item"),
                    qty_received=qty_to_receive,
                    qty_rejected=0.0,
                    unit_of_measure=po_item.get("unit_of_measure", "each"),
                    inspection_notes="Inspected at dock. Quality verified.",
                )
            )

    rec_date = None
    if received_date:
        try:
            rec_date = date.fromisoformat(received_date)
        except ValueError:
            pass

    grn_create = GoodsReceiptCreate(
        purchase_order_id=po.id,
        received_date=rec_date or date.today(),
        received_by=user_id or "Receiving Dock Manager",
        delivery_note_ref=delivery_note_ref or f"DN-{po.po_number}",
        carrier=carrier or "Express Freight Logistics",
        notes=notes,
        line_items=grn_items,
        auto_confirm=auto_confirm,
    )

    grn_svc = GoodsReceiptService(db)
    grn = await grn_svc.create_receipt(org_id, grn_create, user_id=user_id)

    # Re-fetch updated PO status
    po_after = await po_svc.get_po(po.id, org_id)

    return {
        "action": "record_receipt",
        "grn_id": str(grn.id),
        "grn_number": grn.grn_number,
        "purchase_order_id": str(grn.purchase_order_id),
        "po_number": grn.po_number or po.po_number,
        "supplier_name": grn.supplier_name or po.company_name,
        "status": grn.status,
        "po_status": po_after.status,
        "received_date": grn.received_date.isoformat(),
        "items_count": len(grn.line_items),
        "delivery_note_ref": grn.delivery_note_ref,
    }


# ── Phase 4 Tools: Invoices & 3-Way Matching ──────────────────────────────────

async def tool_process_invoice(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None,
    po_id: str | None = None,
    invoice_number: str | None = None,
    supplier_name: str | None = None,
    amount: float | None = None,
    currency: str = "USD",
    line_items: list[dict[str, Any]] | None = None,
    notes: str | None = None,
    auto_match: bool = True,
) -> dict[str, Any]:
    """
    Ingest or create a purchase invoice against a PO and optionally trigger auto-matching.
    """
    from app.modules.invoices.schemas import InvoiceCreate, InvoiceLineItemInput
    from app.modules.invoices.service import InvoiceService
    from app.modules.spend.models import PurchaseOrder

    # Resolve PO if provided
    resolved_po_uuid: uuid.UUID | None = None
    if po_id:
        try:
            resolved_po_uuid = uuid.UUID(po_id)
        except ValueError:
            stmt = select(PurchaseOrder.id).where(
                PurchaseOrder.org_id == org_id,
                PurchaseOrder.po_number.ilike(po_id.strip()),
                PurchaseOrder.deleted_at.is_(None),
            )
            resolved_po_uuid = (await db.execute(stmt)).scalar_one_or_none()

    if not resolved_po_uuid:
        # Pick latest receivable or active PO
        stmt = (
            select(PurchaseOrder.id)
            .where(
                PurchaseOrder.org_id == org_id,
                PurchaseOrder.status.in_(["approved", "sent", "acknowledged", "partially_received", "received"]),
                PurchaseOrder.deleted_at.is_(None),
            )
            .order_by(PurchaseOrder.created_at.desc())
            .limit(1)
        )
        resolved_po_uuid = (await db.execute(stmt)).scalar_one_or_none()

    inv_lines: list[InvoiceLineItemInput] = []
    if line_items:
        for idx, it in enumerate(line_items):
            inv_lines.append(
                InvoiceLineItemInput(
                    po_line_index=int(it.get("po_line_index", idx)),
                    item_id=uuid.UUID(it["item_id"]) if it.get("item_id") else None,
                    item_code=it.get("item_code"),
                    description=it.get("description", "Material Supply"),
                    quantity=float(it.get("quantity", 1.0)),
                    unit_price=float(it.get("unit_price", 0.0)),
                    total_amount=float(it["total_amount"]) if it.get("total_amount") is not None else None,
                    unit_of_measure=it.get("unit_of_measure", "each"),
                )
            )

    create_data = InvoiceCreate(
        po_id=resolved_po_uuid,
        supplier_name=supplier_name,
        invoice_number=invoice_number,
        amount=amount,
        currency=currency,
        line_items=inv_lines,
        notes=notes,
        auto_match=auto_match,
    )

    svc = InvoiceService(db)
    inv = await svc.create_invoice(org_id, create_data, user_id=user_id)

    return {
        "action": "process_invoice",
        "invoice_id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "supplier_name": inv.supplier_name,
        "po_number": inv.po_number,
        "grn_number": inv.grn_number,
        "amount": inv.amount,
        "currency": inv.currency,
        "match_status": inv.match_status,
        "payment_status": inv.payment_status,
        "exceptions_count": len(inv.match_exceptions),
        "items_count": len(inv.line_items),
        "approved": inv.approved_by is not None,
    }


async def tool_match_invoice(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    user_id: str | None = None,
    invoice_id: str,
    price_tolerance_pct: float = 2.0,
    qty_tolerance_pct: float = 5.0,
    amount_tolerance_abs: float = 500.0,
) -> dict[str, Any]:
    """
    Execute deterministic 2-way or 3-way matching on an invoice.
    """
    from app.modules.invoices.matching_engine import MatchTolerances
    from app.modules.invoices.service import InvoiceNotFound, InvoiceService
    from app.modules.spend.models import SpendRecord

    target_inv_uuid: uuid.UUID | None = None
    try:
        target_inv_uuid = uuid.UUID(invoice_id)
    except ValueError:
        stmt = select(SpendRecord.id).where(
            SpendRecord.org_id == org_id,
            SpendRecord.invoice_number.ilike(invoice_id.strip()),
            SpendRecord.deleted_at.is_(None),
        )
        target_inv_uuid = (await db.execute(stmt)).scalar_one_or_none()

    if not target_inv_uuid:
        # Check latest invoice
        stmt = (
            select(SpendRecord.id)
            .where(SpendRecord.org_id == org_id, SpendRecord.deleted_at.is_(None))
            .order_by(SpendRecord.created_at.desc())
            .limit(1)
        )
        target_inv_uuid = (await db.execute(stmt)).scalar_one_or_none()

    if not target_inv_uuid:
        raise ProcurementToolError(f"Invoice '{invoice_id}' not found.")

    tolerances = MatchTolerances(
        price_tolerance_pct=price_tolerance_pct,
        qty_tolerance_pct=qty_tolerance_pct,
        amount_tolerance_abs=amount_tolerance_abs,
    )

    svc = InvoiceService(db)
    try:
        result = await svc.match_invoice(
            target_inv_uuid,
            org_id,
            user_id=user_id,
            tolerances=tolerances,
        )
    except InvoiceNotFound:
        raise ProcurementToolError(f"Invoice '{invoice_id}' not found.")

    return {
        "action": "match_invoice",
        "invoice_id": str(result.invoice_id),
        "invoice_number": result.invoice_number,
        "match_type": result.match_type,
        "match_status": result.match_status,
        "po_number": result.po_number,
        "grn_number": result.grn_number,
        "supplier_name": result.supplier_name,
        "within_tolerance": result.within_tolerance,
        "summary": result.summary,
        "exceptions_count": len(result.exceptions),
        "exceptions": [e.model_dump() for e in result.exceptions],
        "line_matches": [lm.model_dump() for lm in result.line_matches],
        "tolerances_used": result.tolerances_used,
    }


