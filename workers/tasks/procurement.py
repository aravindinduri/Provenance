"""
workers/tasks/procurement.py — Celery background tasks for procurement and invoice matching.

Architecture reference: §4, Phase 4 P4.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from celery import shared_task

from app.db.session import get_session_factory
from app.modules.invoices.matching_engine import MatchTolerances
from app.modules.invoices.repository import InvoiceRepository
from app.modules.invoices.service import InvoiceService

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    name="workers.tasks.procurement.auto_match_invoices",
    max_retries=3,
    default_retry_delay=30,
    queue="ingest",
)
def auto_match_invoices(
    self,
    org_id: str | None = None,
) -> dict[str, Any]:
    """
    Celery task to discover unmatched invoices with linked POs and run
    deterministic 2-way / 3-way matching.
    """
    return asyncio.run(_async_auto_match_invoices(self, org_id))


@shared_task(
    bind=True,
    name="workers.tasks.procurement.match_single_invoice",
    max_retries=3,
    default_retry_delay=15,
    queue="ingest",
)
def match_single_invoice(
    self,
    invoice_id: str,
    org_id: str,
) -> dict[str, Any]:
    """
    Run 3-way/2-way match for a specific invoice asynchronously.
    """
    return asyncio.run(_async_match_single_invoice(self, invoice_id, org_id))


async def _async_auto_match_invoices(
    task: Any,
    org_id_str: str | None,
) -> dict[str, Any]:
    factory = get_session_factory()
    target_org_uuid = uuid.UUID(org_id_str) if org_id_str else None

    processed_count = 0
    matched_count = 0
    exception_count = 0

    async with factory() as session:
        repo = InvoiceRepository(session)
        unmatched_invoices = await repo.get_unmatched(target_org_uuid)

        if not unmatched_invoices:
            logger.info("auto_match_invoices_no_records_pending")
            return {
                "status": "success",
                "processed": 0,
                "matched": 0,
                "exceptions": 0,
            }

        svc = InvoiceService(session)
        tolerances = MatchTolerances()

        for inv in unmatched_invoices:
            try:
                res = await svc.match_invoice(
                    inv.id,
                    inv.org_id,
                    user_id="Celery Auto-Match Worker",
                    tolerances=tolerances,
                )
                processed_count += 1
                if res.within_tolerance:
                    matched_count += 1
                else:
                    exception_count += 1
            except Exception as exc:
                logger.error(
                    "auto_match_single_invoice_failed",
                    invoice_id=str(inv.id),
                    error=str(exc),
                )

        await session.commit()

    logger.info(
        "auto_match_invoices_completed",
        processed=processed_count,
        matched=matched_count,
        exceptions=exception_count,
    )
    return {
        "status": "success",
        "processed": processed_count,
        "matched": matched_count,
        "exceptions": exception_count,
    }


async def _async_match_single_invoice(
    task: Any,
    invoice_id_str: str,
    org_id_str: str,
) -> dict[str, Any]:
    factory = get_session_factory()
    inv_uuid = uuid.UUID(invoice_id_str)
    org_uuid = uuid.UUID(org_id_str)

    async with factory() as session:
        svc = InvoiceService(session)
        try:
            res = await svc.match_invoice(
                inv_uuid,
                org_uuid,
                user_id="Celery Worker",
            )
            await session.commit()
            return {
                "status": "success",
                "invoice_id": str(res.invoice_id),
                "match_status": res.match_status,
                "within_tolerance": res.within_tolerance,
                "exceptions_count": len(res.exceptions),
            }
        except Exception as exc:
            await session.rollback()
            logger.error("match_single_invoice_task_failed", error=str(exc))
            raise task.retry(exc=exc) from exc
