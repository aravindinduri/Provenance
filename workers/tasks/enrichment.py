"""
workers/tasks/enrichment.py — Background tasks for entity enrichment and hierarchy seeding.

Architecture reference: §E.1 #2, §G.1, Phase 9.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from celery import shared_task

from app.db.session import get_session_factory
from app.modules.companies.gleif_enrichment import GleifEnrichmentService

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    name="workers.tasks.enrichment.enrich_company_gleif",
    max_retries=3,
    default_retry_delay=60,
    queue="ingest",
)
def enrich_company_gleif(
    self,
    company_id: str,
    org_id: str | None = None,
) -> dict[str, Any]:
    """
    Celery task to enrich a canonical company via GLEIF and seed owned_by edges.
    """
    return asyncio.run(_async_enrich_company(self, company_id, org_id))


async def _async_enrich_company(
    task: Any,
    company_id_str: str,
    org_id_str: str | None,
) -> dict[str, Any]:
    factory = get_session_factory()
    company_uuid = uuid.UUID(company_id_str)
    org_uuid = uuid.UUID(org_id_str) if org_id_str else None

    async with factory() as session:
        svc = GleifEnrichmentService(session)
        try:
            result = await svc.enrich_company(company_uuid, org_uuid)
            await session.commit()
            logger.info("gleif_enrichment_task_completed", result=result)
            return result
        except Exception as exc:
            await session.rollback()
            logger.error("gleif_enrichment_task_failed", error=str(exc))
            raise task.retry(exc=exc) from exc
