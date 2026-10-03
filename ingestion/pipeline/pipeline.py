"""
Ingestion pipeline orchestrator.
Architecture reference: §F.1 (Connector -> RawStore -> Normalize -> Dedupe).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.modules.events.models import DataSource
from ingestion.connectors.base import SourceConnector
from ingestion.connectors.registry import get_connector
from ingestion.pipeline.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from ingestion.pipeline.dedupe import (
    DedupeResult,
    process_and_dedupe_record_async,
    process_and_dedupe_record_sync,
)
from ingestion.pipeline.raw_store import get_raw_store

logger = structlog.get_logger(__name__)


@dataclass
class IngestionSummary:
    source_key: str
    total_fetched: int = 0
    new_records: int = 0
    duplicates: int = 0
    revisions: int = 0
    next_cursor: str | None = None
    results: list[DedupeResult] = field(default_factory=list)


class IngestionPipeline:
    """
    Executes the ingestion stages:
    1. Check Circuit Breaker
    2. Connector.fetch()
    3. For each item: RawStore -> Normalize -> Dedupe
    4. Record success/failure on DataSource
    """

    def __init__(self, raw_store=None) -> None:
        self.raw_store = raw_store or get_raw_store()

    def run_sync(
        self,
        session: Session,
        connector: SourceConnector | str,
        cursor: str | None = None,
        force: bool = False,
    ) -> IngestionSummary:
        """
        Synchronous pipeline run (used by sync Celery workers or unit tests).
        """
        if isinstance(connector, str):
            conn = get_connector(connector)
            source_key = connector
        else:
            conn = connector
            source_key = conn.source_id

        # 1. Check Circuit Breaker
        if not force and not CircuitBreaker.is_allowed_sync(session, source_key):
            raise CircuitBreakerOpenException(source_key, 5, until=None)  # type: ignore[arg-type]

        # 2. Get DataSource record
        source_rec = session.execute(
            select(DataSource).where(DataSource.source_key == source_key)
        ).scalar_one_or_none()

        if not source_rec:
            # Create DataSource record if missing (e.g. in test env)
            source_rec = DataSource(
                id=uuid.uuid4(),
                source_key=source_key,
                name=source_key.replace("_", " ").title(),
                source_type=conn.source_type,
                reliability=conn.reliability,
                is_enabled=True,
                status="healthy",
                consecutive_failures=0,
            )
            session.add(source_rec)
            session.commit()
            session.refresh(source_rec)

        summary = IngestionSummary(source_key=source_key)

        try:
            # 3. Fetch (run async fetch synchronously using asyncio.run or loop)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # In nested event loop, use run_until_complete in a separate thread if needed
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    fetch_res = pool.submit(asyncio.run, conn.fetch(cursor)).result()
            else:
                fetch_res = loop.run_until_complete(conn.fetch(cursor))

            summary.total_fetched = len(fetch_res.items)
            summary.next_cursor = fetch_res.next_cursor

            # 4. Process each item: RawStore -> Normalize -> Dedupe
            for item in fetch_res.items:
                chash = conn.content_hash(item)
                # Store raw item in RawStore
                raw_s3_key = loop.run_until_complete(
                    self.raw_store.store(
                        source_id=source_key,
                        content_hash=chash,
                        payload=item,
                    )
                )

                # Pure normalization
                normalized = conn.normalize(item)

                # Dedupe and DB write
                dedupe_res = process_and_dedupe_record_sync(
                    session=session,
                    source_db_id=source_rec.id,
                    normalized=normalized,
                    raw_s3_key=raw_s3_key,
                )

                summary.results.append(dedupe_res)
                if dedupe_res.is_new:
                    summary.new_records += 1
                elif dedupe_res.is_duplicate:
                    summary.duplicates += 1
                elif dedupe_res.is_revision:
                    summary.revisions += 1

            # 5. Success
            CircuitBreaker.record_success_sync(session, source_key)
            logger.info(
                "ingestion_pipeline_complete",
                source_key=source_key,
                total=summary.total_fetched,
                new=summary.new_records,
                duplicates=summary.duplicates,
                revisions=summary.revisions,
            )
            return summary

        except Exception as exc:
            CircuitBreaker.record_failure_sync(session, source_key, str(exc))
            logger.error("ingestion_pipeline_failed", source_key=source_key, error=str(exc))
            raise

    async def run_async(
        self,
        session: AsyncSession,
        connector: SourceConnector | str,
        cursor: str | None = None,
        force: bool = False,
    ) -> IngestionSummary:
        """
        Asynchronous pipeline run.
        """
        if isinstance(connector, str):
            conn = get_connector(connector)
            source_key = connector
        else:
            conn = connector
            source_key = conn.source_id

        if not force and not await CircuitBreaker.is_allowed(session, source_key):
            raise CircuitBreakerOpenException(source_key, 5, until=None)  # type: ignore[arg-type]

        res = await session.execute(
            select(DataSource).where(DataSource.source_key == source_key)
        )
        source_rec = res.scalar_one_or_none()

        if not source_rec:
            source_rec = DataSource(
                id=uuid.uuid4(),
                source_key=source_key,
                name=source_key.replace("_", " ").title(),
                source_type=conn.source_type,
                reliability=conn.reliability,
                is_enabled=True,
                status="healthy",
                consecutive_failures=0,
            )
            session.add(source_rec)
            await session.commit()
            await session.refresh(source_rec)

        summary = IngestionSummary(source_key=source_key)

        try:
            fetch_res = await conn.fetch(cursor)
            summary.total_fetched = len(fetch_res.items)
            summary.next_cursor = fetch_res.next_cursor

            for item in fetch_res.items:
                chash = conn.content_hash(item)
                raw_s3_key = await self.raw_store.store(
                    source_id=source_key,
                    content_hash=chash,
                    payload=item,
                )

                normalized = conn.normalize(item)

                dedupe_res = await process_and_dedupe_record_async(
                    session=session,
                    source_db_id=source_rec.id,
                    normalized=normalized,
                    raw_s3_key=raw_s3_key,
                )

                summary.results.append(dedupe_res)
                if dedupe_res.is_new:
                    summary.new_records += 1
                elif dedupe_res.is_duplicate:
                    summary.duplicates += 1
                elif dedupe_res.is_revision:
                    summary.revisions += 1

            await CircuitBreaker.record_success(session, source_key)
            return summary

        except Exception as exc:
            await CircuitBreaker.record_failure(session, source_key, str(exc))
            raise
