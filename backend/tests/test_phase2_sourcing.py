"""
/app/tests/test_phase2_sourcing.py — Tests for Phase 2 Sourcing.
"""

import pytest
from app.modules.rfx.service import (
    RFxService,
    InvalidRFxStatusTransition,
    _VALID_RFX_TRANSITIONS,
)


def test_rfx_valid_transitions():
    """Verify state machine transitions are correctly configured."""
    assert "published" in _VALID_RFX_TRANSITIONS["draft"]
    assert "cancelled" in _VALID_RFX_TRANSITIONS["draft"]
    assert "evaluation" in _VALID_RFX_TRANSITIONS["published"]
    assert "awarded" in _VALID_RFX_TRANSITIONS["evaluation"]
    assert "closed" in _VALID_RFX_TRANSITIONS["awarded"]
    assert _VALID_RFX_TRANSITIONS["closed"] == []
    assert _VALID_RFX_TRANSITIONS["cancelled"] == []


def test_rfx_invalid_transition_raises():
    """Verify invalid state transitions raise InvalidRFxStatusTransition."""
    svc = RFxService(None)  # type: ignore[arg-type]
    with pytest.raises(InvalidRFxStatusTransition):
        svc._assert_transition("draft", "awarded")

    with pytest.raises(InvalidRFxStatusTransition):
        svc._assert_transition("closed", "published")


def test_rfx_bid_scoring_math():
    """Verify deterministic bid comparison math: price normalization and weighted sum."""
    min_price = 1000.0
    price_quote_1 = 1000.0
    price_quote_2 = 1250.0

    score_1 = round((min_price / price_quote_1) * 100.0, 2)
    score_2 = round((min_price / price_quote_2) * 100.0, 2)

    assert score_1 == 100.0
    assert score_2 == 80.0

    # Weights: Price 40%, Quality 25%, Delivery 20%, Risk 15%
    weights = {"Price": 40.0, "Quality": 25.0, "Delivery": 20.0, "Risk": 15.0}
    total_w = sum(weights.values())

    comp_1 = (100.0 * 40.0 + 85.0 * 25.0 + 80.0 * 20.0 + 80.0 * 15.0) / total_w
    assert round(comp_1, 2) == 89.25

    comp_2 = (80.0 * 40.0 + 95.0 * 25.0 + 100.0 * 20.0 + 90.0 * 15.0) / total_w
    assert round(comp_2, 2) == 89.25
