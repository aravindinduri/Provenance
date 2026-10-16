"""
tests/unit/test_phase4_matching.py — Unit tests for Phase 4 Deterministic 2-Way and 3-Way Matching Engine.
"""

import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

import app.db.models  # noqa: F401
from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.invoices.matching_engine import (
    MatchTolerances,
    evaluate_invoice_match,
)
from app.modules.spend.models import PurchaseOrder, SpendRecord


def test_3way_match_successful_within_tolerances():
    """
    Architecture §8.3 test case:
    PO: 500 x $4,200 ($2,100,000)
    GRN: 495 received (5 short acknowledged)
    Invoice: 495 x $4,250 ($2,103,750)
    Price variance: +1.19% (within 2% tolerance)
    Quantity: 495 vs 495 (exact match)
    Verdict: MATCHED_3WAY with notes
    """
    po_id = uuid.uuid4()
    org_id = uuid.uuid4()

    po = PurchaseOrder(
        id=po_id,
        org_id=org_id,
        po_number="PO-2026-0042",
        status="sent",
        total_amount=2100000.0,
        currency="USD",
        line_items=[
            {
                "po_line_index": 0,
                "description": "Stainless Steel Sheet 304",
                "quantity": 500.0,
                "unit_price": 4200.0,
            }
        ],
    )

    grn = GoodsReceipt(
        id=uuid.uuid4(),
        org_id=org_id,
        grn_number="GRN-2026-0010",
        purchase_order_id=po_id,
        status="confirmed",
        received_date=date.today(),
        line_items=[
            {
                "po_line_index": 0,
                "description": "Stainless Steel Sheet 304",
                "qty_received": 495.0,
                "qty_rejected": 0.0,
            }
        ],
    )

    invoice = SpendRecord(
        id=uuid.uuid4(),
        org_id=org_id,
        invoice_number="INV-2026-0001",
        po_id=po_id,
        amount=2103750.0,
        currency="USD",
        line_items=[
            {
                "po_line_index": 0,
                "description": "Stainless Steel Sheet 304",
                "quantity": 495.0,
                "unit_price": 4250.0,
                "total_amount": 2103750.0,
            }
        ],
    )

    # Tolerances: 2% price, 5% qty, $30,000 absolute amount tolerance
    tolerances = MatchTolerances(
        price_tolerance_pct=2.0,
        qty_tolerance_pct=5.0,
        amount_tolerance_abs=30000.0,
    )

    result = evaluate_invoice_match(invoice, po, grn, tolerances)

    assert result.match_type == "3way"
    assert result.match_status == "matched_3way"
    assert result.within_tolerance is True
    assert len(result.exceptions) == 0
    assert len(result.line_matches) == 1
    assert result.line_matches[0].price_variance_pct == 1.19
    assert result.line_matches[0].status == "matched"
    assert "partial delivery" in result.line_matches[0].notes


def test_2way_match_successful():
    """Verify 2-way match against PO when no GRN is required/provided."""
    po_id = uuid.uuid4()
    org_id = uuid.uuid4()

    po = PurchaseOrder(
        id=po_id,
        org_id=org_id,
        po_number="PO-2026-0099",
        status="approved",
        total_amount=5000.0,
        currency="USD",
        line_items=[
            {
                "po_line_index": 0,
                "description": "Software Subscription Services",
                "quantity": 1.0,
                "unit_price": 5000.0,
            }
        ],
    )

    invoice = SpendRecord(
        id=uuid.uuid4(),
        org_id=org_id,
        invoice_number="INV-2026-0099",
        po_id=po_id,
        amount=5000.0,
        currency="USD",
        line_items=[
            {
                "po_line_index": 0,
                "description": "Software Subscription Services",
                "quantity": 1.0,
                "unit_price": 5000.0,
            }
        ],
    )

    result = evaluate_invoice_match(invoice, po, None)

    assert result.match_type == "2way"
    assert result.match_status == "matched_2way"
    assert result.within_tolerance is True
    assert len(result.exceptions) == 0


def test_price_variance_exceeds_tolerance_flags_exception():
    """Verify that price variance outside tolerance triggers an exception."""
    po_id = uuid.uuid4()
    org_id = uuid.uuid4()

    po = PurchaseOrder(
        id=po_id,
        org_id=org_id,
        po_number="PO-2026-0100",
        status="sent",
        total_amount=10000.0,
        line_items=[
            {
                "po_line_index": 0,
                "description": "Custom Heat Sink",
                "quantity": 100.0,
                "unit_price": 100.0,
            }
        ],
    )

    # Invoiced at $120.00 (+20% variance vs 2% limit)
    invoice = SpendRecord(
        id=uuid.uuid4(),
        org_id=org_id,
        invoice_number="INV-2026-0100",
        po_id=po_id,
        amount=12000.0,
        currency="USD",
        line_items=[
            {
                "po_line_index": 0,
                "description": "Custom Heat Sink",
                "quantity": 100.0,
                "unit_price": 120.0,
            }
        ],
    )

    result = evaluate_invoice_match(invoice, po, None)

    assert result.match_status == "exception"
    assert result.within_tolerance is False
    assert any(e.code == "price_variance" for e in result.exceptions)


def test_quantity_mismatch_flags_exception():
    """Verify that quantity discrepancy outside tolerance triggers an exception."""
    po_id = uuid.uuid4()
    org_id = uuid.uuid4()

    po = PurchaseOrder(
        id=po_id,
        org_id=org_id,
        po_number="PO-2026-0101",
        status="acknowledged",
        total_amount=5000.0,
        line_items=[
            {
                "po_line_index": 0,
                "description": "Industrial Valves",
                "quantity": 50.0,
                "unit_price": 100.0,
            }
        ],
    )

    grn = GoodsReceipt(
        id=uuid.uuid4(),
        org_id=org_id,
        grn_number="GRN-2026-0101",
        purchase_order_id=po_id,
        status="confirmed",
        received_date=date.today(),
        line_items=[
            {
                "po_line_index": 0,
                "description": "Industrial Valves",
                "qty_received": 40.0,  # Dock received only 40
            }
        ],
    )

    # Invoiced for full 50 (+25% delta over 40 delivered)
    invoice = SpendRecord(
        id=uuid.uuid4(),
        org_id=org_id,
        invoice_number="INV-2026-0101",
        po_id=po_id,
        amount=5000.0,
        currency="USD",
        line_items=[
            {
                "po_line_index": 0,
                "description": "Industrial Valves",
                "quantity": 50.0,
                "unit_price": 100.0,
            }
        ],
    )

    result = evaluate_invoice_match(invoice, po, grn)

    assert result.match_status == "exception"
    assert result.within_tolerance is False
    assert any(e.code == "quantity_mismatch" for e in result.exceptions)


def test_missing_po_flags_critical_exception():
    """Verify that invoice without linked PO cannot be matched."""
    invoice = SpendRecord(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        invoice_number="INV-ORPHAN",
        amount=1000.0,
        currency="USD",
        line_items=[],
    )

    result = evaluate_invoice_match(invoice, None, None)

    assert result.match_status == "exception"
    assert result.match_type == "unmatched"
    assert any(e.code == "missing_po" for e in result.exceptions)


def test_unapproved_po_blocks_matching():
    """Verify draft PO triggers unapproved_po exception."""
    po_id = uuid.uuid4()
    org_id = uuid.uuid4()

    po = PurchaseOrder(
        id=po_id,
        org_id=org_id,
        po_number="PO-DRAFT",
        status="draft",  # Draft PO
        total_amount=1000.0,
        line_items=[],
    )

    invoice = SpendRecord(
        id=uuid.uuid4(),
        org_id=org_id,
        invoice_number="INV-2026-0002",
        po_id=po_id,
        amount=1000.0,
        currency="USD",
        line_items=[],
    )

    result = evaluate_invoice_match(invoice, po, None)

    assert result.match_status == "exception"
    assert any(e.code == "unapproved_po" for e in result.exceptions)
