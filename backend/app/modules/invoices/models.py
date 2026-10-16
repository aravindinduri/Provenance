"""
app/modules/invoices/models.py — Purchase Invoice models.

In Provenance, invoices are persisted in the tenant-scoped, RLS-protected
`spend_records` table, extended in Phase 4 with full 3-way matching, line items,
and payment tracking.
"""

from __future__ import annotations

from app.modules.spend.models import SpendRecord

# Invoice is the domain model alias for SpendRecord with Phase 4 matching fields
Invoice = SpendRecord

__all__ = ["Invoice", "SpendRecord"]
