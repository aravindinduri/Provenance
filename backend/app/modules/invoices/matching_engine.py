"""
app/modules/invoices/matching_engine.py — Deterministic 2-Way & 3-Way Matching Engine.

Zero hallucinations, pure arithmetic comparison against PO and GRN:
  - 2-Way Match: PO vs Invoice (Price & Quantity)
  - 3-Way Match: PO vs Goods Receipt Note (GRN) vs Invoice (Price, Quantity, Delivery Verification)
  - Configurable tolerances:
      Price variance: default ±2.0%
      Quantity variance: default ±5.0%
      Amount delta: default ±$500.00
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.modules.goods_receipts.models import GoodsReceipt
from app.modules.invoices.schemas import (
    InvoiceMatchResult,
    LineMatchDetail,
    MatchExceptionItem,
)
from app.modules.spend.models import PurchaseOrder, SpendRecord


@dataclass
class MatchTolerances:
    price_tolerance_pct: float = 2.0
    qty_tolerance_pct: float = 5.0
    amount_tolerance_abs: float = 500.0


def evaluate_invoice_match(
    invoice: SpendRecord,
    po: PurchaseOrder | None,
    grn: GoodsReceipt | None = None,
    tolerances: MatchTolerances | None = None,
) -> InvoiceMatchResult:
    """
    Evaluates 2-way or 3-way match deterministically between an Invoice, PO, and optional GRN.
    """
    tol = tolerances or MatchTolerances()
    tolerances_dict = {
        "price_tolerance_pct": tol.price_tolerance_pct,
        "qty_tolerance_pct": tol.qty_tolerance_pct,
        "amount_tolerance_abs": tol.amount_tolerance_abs,
    }

    exceptions: list[MatchExceptionItem] = []
    line_matches: list[LineMatchDetail] = []

    # ── Rule 1: Validate PO existence ─────────────────────────────────────────
    if not po:
        exceptions.append(
            MatchExceptionItem(
                code="missing_po",
                severity="critical",
                message="Invoice is not linked to any Purchase Order. 3-way/2-way matching requires a valid PO.",
            )
        )
        return InvoiceMatchResult(
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number or "INV-UNKNOWN",
            match_type="unmatched",
            match_status="exception",
            po_id=None,
            po_number=None,
            goods_receipt_id=None,
            grn_number=None,
            supplier_name=None,
            within_tolerance=False,
            summary="Matching failed: Missing linked Purchase Order.",
            line_matches=[],
            exceptions=exceptions,
            tolerances_used=tolerances_dict,
        )

    # ── Rule 2: Validate PO approval status ────────────────────────────────────
    valid_po_statuses = {
        "approved",
        "sent",
        "acknowledged",
        "partially_received",
        "received",
        "closed",
    }
    if po.status not in valid_po_statuses:
        exceptions.append(
            MatchExceptionItem(
                code="unapproved_po",
                severity="critical",
                message=(
                    f"Purchase Order {po.po_number} has status '{po.status}'. "
                    f"POs must be approved and dispatched before invoice verification."
                ),
                expected="approved",
                actual=po.status,
            )
        )

    # ── Rule 3: Determine 2-Way vs 3-Way Match ─────────────────────────────────
    match_type: "2way" | "3way" = "3way" if grn is not None else "2way"

    # If 3-Way match, check GRN confirmation
    if grn and grn.status not in ("confirmed", "partial"):
        exceptions.append(
            MatchExceptionItem(
                code="unconfirmed_receipt",
                severity="warning",
                message=f"Goods Receipt Note {grn.grn_number} is in '{grn.status}' status (not yet confirmed on dock).",
                expected="confirmed",
                actual=grn.status,
            )
        )

    # ── Line Item Comparison ──────────────────────────────────────────────────
    po_lines: list[dict[str, Any]] = (
        po.line_items if isinstance(po.line_items, list) else []
    )
    inv_lines: list[dict[str, Any]] = (
        invoice.line_items if isinstance(invoice.line_items, list) else []
    )
    grn_lines: list[dict[str, Any]] = (
        grn.line_items if grn and isinstance(grn.line_items, list) else []
    )

    expected_total_amount = 0.0

    # Match each invoice line to corresponding PO line
    # (By po_line_index if present, else by index order)
    max_lines = max(len(inv_lines), len(po_lines), 1)

    for idx in range(max_lines):
        inv_item = (
            inv_lines[idx]
            if idx < len(inv_lines)
            else {
                "description": "Unbilled line",
                "quantity": 0.0,
                "unit_price": 0.0,
                "total_amount": 0.0,
            }
        )
        po_item = (
            po_lines[idx]
            if idx < len(po_lines)
            else {
                "description": "Unordered line",
                "quantity": 0.0,
                "unit_price": 0.0,
                "total_price": 0.0,
            }
        )

        po_line_idx = int(inv_item.get("po_line_index", idx))
        desc = inv_item.get("description") or po_item.get("description", f"Line {idx+1}")
        item_code = inv_item.get("item_code") or po_item.get("item_code")

        inv_qty = float(inv_item.get("quantity", 0.0))
        inv_price = float(inv_item.get("unit_price", 0.0))

        po_qty = float(po_item.get("quantity", 0.0))
        po_price = float(po_item.get("unit_price", 0.0))

        grn_qty: float | None = None
        target_qty = po_qty

        if match_type == "3way" and grn:
            # Locate matching line in GRN
            matched_grn = next(
                (g for g in grn_lines if int(g.get("po_line_index", -1)) == po_line_idx),
                None,
            )
            if not matched_grn and idx < len(grn_lines):
                matched_grn = grn_lines[idx]

            if matched_grn:
                grn_qty = float(matched_grn.get("qty_received", 0.0))
                target_qty = grn_qty
            else:
                grn_qty = 0.0
                target_qty = 0.0

        expected_total_amount += target_qty * po_price

        # Quantity arithmetic
        qty_delta = round(inv_qty - target_qty, 4)
        if target_qty > 0:
            qty_var_pct = round((abs(qty_delta) / target_qty) * 100, 2)
        elif inv_qty == 0:
            qty_var_pct = 0.0
        else:
            qty_var_pct = 100.0

        # Price arithmetic
        if po_price > 0:
            price_var_pct = round(((inv_price - po_price) / po_price) * 100, 2)
        elif inv_price == 0:
            price_var_pct = 0.0
        else:
            price_var_pct = 100.0

        # Tolerance checks
        price_ok = abs(price_var_pct) <= tol.price_tolerance_pct
        qty_ok = qty_var_pct <= tol.qty_tolerance_pct

        notes_parts: list[str] = []

        if not price_ok:
            severity = "critical" if abs(price_var_pct) > 5.0 else "warning"
            sign = "+" if price_var_pct > 0 else ""
            msg = (
                f"Line #{idx+1} '{desc}': Invoiced unit price ${inv_price:,.2f} differs from "
                f"PO unit price ${po_price:,.2f} by {sign}{price_var_pct:.2f}% "
                f"(threshold: ±{tol.price_tolerance_pct}%)."
            )
            exceptions.append(
                MatchExceptionItem(
                    code="price_variance",
                    severity=severity,
                    message=msg,
                    line_index=idx,
                    expected=po_price,
                    actual=inv_price,
                    variance_pct=price_var_pct,
                )
            )
            notes_parts.append(f"Price variance {sign}{price_var_pct:.1f}%")

        if not qty_ok:
            severity = "critical" if qty_var_pct > 10.0 else "warning"
            ref_label = "GRN received" if match_type == "3way" else "PO ordered"
            msg = (
                f"Line #{idx+1} '{desc}': Invoiced qty {inv_qty:,.2f} differs from "
                f"{ref_label} qty {target_qty:,.2f} by {qty_var_pct:.2f}% "
                f"(threshold: ±{tol.qty_tolerance_pct}%)."
            )
            exceptions.append(
                MatchExceptionItem(
                    code="quantity_mismatch",
                    severity=severity,
                    message=msg,
                    line_index=idx,
                    expected=target_qty,
                    actual=inv_qty,
                    variance_pct=qty_var_pct,
                )
            )
            notes_parts.append(f"Qty delta: {qty_delta:+g}")

        # Check for partial receipt vs original PO order
        if match_type == "3way" and grn_qty is not None and grn_qty < po_qty:
            shortage = po_qty - grn_qty
            notes_parts.append(f"{shortage:g} units short vs original PO (partial delivery)")

        line_status: "matched" | "variance" = (
            "matched" if (price_ok and qty_ok) else "variance"
        )

        line_matches.append(
            LineMatchDetail(
                po_line_index=po_line_idx,
                item_code=item_code,
                description=desc,
                po_quantity=po_qty,
                grn_quantity=grn_qty,
                invoice_quantity=inv_qty,
                po_unit_price=po_price,
                invoice_unit_price=inv_price,
                price_variance_pct=price_var_pct,
                qty_delta=qty_delta,
                status=line_status,
                notes=" · ".join(notes_parts) if notes_parts else "Exact match within tolerance",
            )
        )

    # ── Rule 4: Total Amount Variance ─────────────────────────────────────────
    invoice_amount = float(invoice.amount)
    amount_delta = round(abs(invoice_amount - expected_total_amount), 2)
    amount_var_pct = (
        round((amount_delta / expected_total_amount) * 100, 2)
        if expected_total_amount > 0
        else 0.0
    )

    if (
        amount_delta > tol.amount_tolerance_abs
        and amount_var_pct > tol.price_tolerance_pct
    ):
        exceptions.append(
            MatchExceptionItem(
                code="total_amount_variance",
                severity="critical",
                message=(
                    f"Invoice total (${invoice_amount:,.2f}) differs from expected total "
                    f"(${expected_total_amount:,.2f}) by ${amount_delta:,.2f} ({amount_var_pct:.2f}%). "
                    f"Exceeds ${tol.amount_tolerance_abs:,.2f} threshold."
                ),
                expected=expected_total_amount,
                actual=invoice_amount,
                variance_pct=amount_var_pct,
            )
        )

    # ── Final Verdict & Status ────────────────────────────────────────────────
    has_critical = any(e.severity == "critical" for e in exceptions)
    within_tolerance = not has_critical and len(exceptions) == 0

    if within_tolerance:
        match_status = "matched_3way" if match_type == "3way" else "matched_2way"
        summary = (
            f"Deterministic {match_type.upper()} match successful. "
            f"All {len(line_matches)} line item(s) and total amount (${invoice_amount:,.2f}) "
            f"fall strictly within configured tolerances."
        )
    else:
        match_status = "exception"
        summary = (
            f"{len(exceptions)} discrepancy/discrepancies detected outside tolerance thresholds. "
            f"Auto-approval blocked; invoice flagged for human exception review."
        )

    supplier_name = None
    if hasattr(po, "company") and po.company:
        supplier_name = getattr(po.company, "legal_name", None)

    return InvoiceMatchResult(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number or "INV-UNKNOWN",
        match_type=match_type,
        match_status=match_status,
        po_id=po.id,
        po_number=po.po_number,
        goods_receipt_id=grn.id if grn else None,
        grn_number=grn.grn_number if grn else None,
        supplier_name=supplier_name,
        within_tolerance=within_tolerance,
        summary=summary,
        line_matches=line_matches,
        exceptions=exceptions,
        tolerances_used=tolerances_dict,
    )
