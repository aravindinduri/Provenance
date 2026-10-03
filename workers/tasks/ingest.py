"""
Celery tasks for external data ingestion and DLQ management.
Architecture reference: §F.4, §16.
Queues: ingest (default for ingestion), ingest_gdelt, ingest_bulk, ingest_api, ingest_html.
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import select

from app.db.session import get_session_factory
from app.modules.events.models import DataSource, DeadLetterQueue
from ingestion.pipeline.circuit_breaker import CircuitBreakerOpenException
from ingestion.pipeline.pipeline import IngestionPipeline

logger = structlog.get_logger(__name__)


async def _async_record_dlq(
    task_name: str,
    payload: dict[str, Any],
    error_msg: str,
    tb_str: str,
    retry_count: int,
) -> uuid.UUID:
    """Records a permanently failed task into dead_letter_queue table."""
    factory = get_session_factory()
    dlq_id = uuid.uuid4()
    async with factory() as session:
        dlq_entry = DeadLetterQueue(
            id=dlq_id,
            task_name=task_name,
            payload=payload,
            error=error_msg,
            traceback=tb_str,
            retry_count=retry_count,
            status="failed",
            created_at=datetime.now(timezone.utc),
        )
        session.add(dlq_entry)
        await session.commit()
    logger.error("dlq_entry_recorded", dlq_id=str(dlq_id), task_name=task_name)
    return dlq_id


async def _async_poll_source(source_key: str, cursor: str | None = None) -> dict[str, Any]:
    """Asynchronous runner for polling a data source."""
    factory = get_session_factory()
    pipeline = IngestionPipeline()
    async with factory() as session:
        summary = await pipeline.run_async(session=session, connector=source_key, cursor=cursor)
        return {
            "source_key": summary.source_key,
            "total_fetched": summary.total_fetched,
            "new_records": summary.new_records,
            "duplicates": summary.duplicates,
            "revisions": summary.revisions,
            "next_cursor": summary.next_cursor,
        }


@shared_task(
    bind=True,
    name="workers.tasks.ingest.poll_source_task",
    max_retries=5,
    default_retry_delay=2,
    acks_late=True,
)
def poll_source_task(self, source_key: str, cursor: str | None = None) -> dict[str, Any]:
    """
    Celery task to poll a specific data source.
    Implements exponential backoff with full jitter per §F.4.
    On final failure, persists task state and traceback to dead_letter_queue.
    """
    logger.info("poll_source_task_starting", source_key=source_key, retry=self.request.retries)
    try:
        return asyncio.run(_async_poll_source(source_key=source_key, cursor=cursor))
    except CircuitBreakerOpenException as cbe:
        logger.warning(
            "poll_source_skipped_circuit_breaker",
            source_key=source_key,
            message=str(cbe),
        )
        return {"status": "skipped", "reason": "circuit_breaker_open", "source_key": source_key}
    except Exception as exc:
        retries = self.request.retries
        tb = traceback.format_exc()
        logger.warning(
            "poll_source_task_exception",
            source_key=source_key,
            retry=retries,
            error=str(exc),
        )

        if retries >= self.max_retries:
            # Final retry exhausted -> write to Dead Letter Queue
            logger.error("poll_source_max_retries_exhausted", source_key=source_key)
            dlq_id = asyncio.run(
                _async_record_dlq(
                    task_name="workers.tasks.ingest.poll_source_task",
                    payload={"source_key": source_key, "cursor": cursor},
                    error_msg=str(exc),
                    tb_str=tb,
                    retry_count=retries,
                )
            )
            return {
                "status": "failed_dlq",
                "dlq_id": str(dlq_id),
                "source_key": source_key,
                "error": str(exc),
            }

        # Exponential backoff: 2^retries seconds
        countdown = 2**retries
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(name="workers.tasks.ingest.poll_all_enabled_sources_task")
def poll_all_enabled_sources_task() -> dict[str, Any]:
    """Enqueues polling tasks for all enabled data sources."""
    async def _get_enabled() -> list[str]:
        factory = get_session_factory()
        async with factory() as session:
            res = await session.execute(
                select(DataSource.source_key).where(
                    DataSource.is_enabled.is_(True),
                    DataSource.status != "failed",
                )
            )
            return list(res.scalars().all())

    sources = asyncio.run(_get_enabled())
    enqueued = []
    for s_key in sources:
        poll_source_task.delay(source_key=s_key)
        enqueued.append(s_key)

    logger.info("enqueued_enabled_sources", count=len(enqueued), sources=enqueued)
    return {"enqueued_sources": enqueued, "count": len(enqueued)}


@shared_task(
    bind=True,
    name="workers.tasks.ingest.replay_dlq_task",
    max_retries=1,
)
def replay_dlq_task(self, dlq_id: str, replayed_by: str | None = None) -> dict[str, Any]:
    """
    Replays a failed task from the Dead Letter Queue.
    On success, updates dead_letter_queue entry with status='replayed', replayed_at=now().
    """
    async def _async_replay() -> dict[str, Any]:
        factory = get_session_factory()
        now = datetime.now(timezone.utc)
        dlq_uuid = uuid.UUID(dlq_id)

        async with factory() as session:
            res = await session.execute(
                select(DeadLetterQueue).where(DeadLetterQueue.id == dlq_uuid)
            )
            entry = res.scalar_one_or_none()
            if not entry:
                raise ValueError(f"DLQ entry {dlq_id} not found")

            payload = entry.payload or {}
            source_key = payload.get("source_key")
            cursor = payload.get("cursor")

            if not source_key:
                raise ValueError(f"DLQ entry {dlq_id} does not contain source_key")

            # Execute pipeline
            pipeline = IngestionPipeline()
            summary = await pipeline.run_async(
                session=session,
                connector=source_key,
                cursor=cursor,
                force=True,  # force past circuit breaker during replay
            )

            # Update DLQ status
            entry.status = "replayed"
            entry.replayed_at = now
            entry.replayed_by = replayed_by or "system"
            await session.commit()

            return {
                "dlq_id": dlq_id,
                "status": "replayed",
                "source_key": source_key,
                "total_fetched": summary.total_fetched,
                "new_records": summary.new_records,
                "duplicates": summary.duplicates,
            }

    try:
        return asyncio.run(_async_replay())
    except Exception as exc:
        logger.error("replay_dlq_failed", dlq_id=dlq_id, error=str(exc))
        raise
