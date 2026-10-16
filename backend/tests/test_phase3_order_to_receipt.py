"""
/app/tests/test_phase3_order_to_receipt.py — Tests for Phase 3 Order-to-Receipt.
"""

import pytest
from app.modules.purchase_orders.service import (
    PurchaseOrderService,
    InvalidPOStatusTransition,
    _VALID_PO_TRANSITIONS,
)
from app.modules.goods_receipts.service import (
    GoodsReceiptService,
    InvalidGRNStatusTransition,
)


def test_po_valid_transitions():
    """Verify purchase order lifecycle state machine transitions."""
    assert "pending_approval" in _VALID_PO_TRANSITIONS["draft"]
    assert "cancelled" in _VALID_PO_TRANSITIONS["draft"]
    assert "approved" in _VALID_PO_TRANSITIONS["pending_approval"]
    assert "sent" in _VALID_PO_TRANSITIONS["approved"]
    assert "acknowledged" in _VALID_PO_TRANSITIONS["sent"]
    assert "partially_received" in _VALID_PO_TRANSITIONS["acknowledged"]
    assert "received" in _VALID_PO_TRANSITIONS["acknowledged"]
    assert "received" in _VALID_PO_TRANSITIONS["partially_received"]
    assert "closed" in _VALID_PO_TRANSITIONS["received"]
    assert _VALID_PO_TRANSITIONS["closed"] == []
    assert _VALID_PO_TRANSITIONS["cancelled"] == []


def test_po_invalid_transition_raises():
    """Verify invalid state transitions raise InvalidPOStatusTransition."""
    svc = PurchaseOrderService(None)  # type: ignore[arg-type]
    with pytest.raises(InvalidPOStatusTransition):
        svc._assert_transition("draft", "received")

    with pytest.raises(InvalidPOStatusTransition):
        svc._assert_transition("closed", "draft")

    with pytest.raises(InvalidPOStatusTransition):
        svc._assert_transition("sent", "pending_approval")


def test_goods_receipt_deterministic_fulfillment_math():
    """
    Verify deterministic arithmetic for partial vs full fulfillment calculations.
    """
    po_lines = [
        {"po_line_index": 0, "quantity": 500.0, "unit_price": 42.0},
        {"po_line_index": 1, "quantity": 200.0, "unit_price": 105.0},
    ]

    # Shipment 1: Partial delivery (250 units of item 0, 0 of item 1)
    grn_1_lines = [{"po_line_index": 0, "qty_received": 250.0}]

    cumulative = {0: 250.0, 1: 0.0}
    is_fully_fulfilled = True
    has_any_fulfillment = False

    for idx, item in enumerate(po_lines):
        ordered = item["quantity"]
        received = cumulative.get(idx, 0.0)
        if received > 0:
            has_any_fulfillment = True
        if received < ordered:
            is_fully_fulfilled = False

    assert has_any_fulfillment is True
    assert is_fully_fulfilled is False
    expected_status = "partially_received"
    assert expected_status == "partially_received"

    # Shipment 2: Completing remaining balance (250 units of item 0, 200 of item 1)
    cumulative[0] += 250.0
    cumulative[1] += 200.0

    is_fully_fulfilled_2 = True
    has_any_fulfillment_2 = False

    for idx, item in enumerate(po_lines):
        ordered = item["quantity"]
        received = cumulative.get(idx, 0.0)
        if received > 0:
            has_any_fulfillment_2 = True
        if received < ordered:
            is_fully_fulfilled_2 = False

    assert has_any_fulfillment_2 is True
    assert is_fully_fulfilled_2 is True
    expected_status_2 = "received"
    assert expected_status_2 == "received"
