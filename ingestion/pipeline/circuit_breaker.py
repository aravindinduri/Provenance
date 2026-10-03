"""
Circuit breaker for external data sources.
Architecture reference: §F.4 (5 consecutive failures -> degraded, pause 30 min).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.modules.events.models import DataSource

logger = structlog.get_logger(__name__)

MAX_CONSECUTIVE_FAILURES = 5
COOLDOWN_MINUTES = 30


class CircuitBreakerOpenException(Exception):
    """Raised when an ingestion attempt is blocked by an open circuit breaker."""

    def __init__(self, source_key: str, consecutive_failures: int, until: datetime):
        self.source_key = source_key
        self.consecutive_failures = consecutive_failures
        self.until = until
        super().__init__(
            f"Circuit breaker OPEN for {source_key!r} ({consecutive_failures} failures). "
            f"Paused until {until.isoformat()}."
        )


class CircuitBreaker:
    """
    Manages failure tracking and health status for DataSource entities.
    5 consecutive failures marks the source 'degraded' and pauses polling for 30 minutes.
    """

    @staticmethod
    def is_allowed_sync(session: Session, source_key: str) -> bool:
        """Synchronous check if source is allowed to run."""
        source = session.execute(
            select(DataSource).where(DataSource.source_key == source_key)
        ).scalar_one_or_none()

        if not source or not source.is_enabled:
            return False

        if source.status == "degraded" and source.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            if source.last_failure_at:
                now = datetime.now(timezone.utc)
                last_fail = source.last_failure_at
                if last_fail.tzinfo is None:
                    last_fail = last_fail.replace(tzinfo=timezone.utc)
                if now - last_fail < timedelta(minutes=COOLDOWN_MINUTES):
                    return False
        return True

    @staticmethod
    def record_success_sync(session: Session, source_key: str) -> None:
        """Records successful poll, resets consecutive_failures and restores healthy status."""
        now = datetime.now(timezone.utc)
        session.execute(
            update(DataSource)
            .where(DataSource.source_key == source_key)
            .values(
                status="healthy",
                consecutive_failures=0,
                last_success_at=now,
                updated_at=now,
            )
        )
        session.commit()
        logger.info("circuit_breaker_healthy", source_key=source_key)

    @staticmethod
    def record_failure_sync(session: Session, source_key: str, error_message: str | None = None) -> None:
        """Records poll failure, increments counter and opens breaker if threshold reached."""
        source = session.execute(
            select(DataSource).where(DataSource.source_key == source_key)
        ).scalar_one_or_none()

        if not source:
            return

        new_failures = source.consecutive_failures + 1
        new_status = "degraded" if new_failures >= MAX_CONSECUTIVE_FAILURES else source.status
        now = datetime.now(timezone.utc)

        source.consecutive_failures = new_failures
        source.status = new_status
        source.last_failure_at = now
        session.commit()

        logger.warning(
            "circuit_breaker_failure_recorded",
            source_key=source_key,
            consecutive_failures=new_failures,
            status=new_status,
            error=error_message,
        )

    @staticmethod
    async def is_allowed(session: AsyncSession, source_key: str) -> bool:
        """Asynchronous check if source is allowed to run."""
        res = await session.execute(
            select(DataSource).where(DataSource.source_key == source_key)
        )
        source = res.scalar_one_or_none()

        if not source or not source.is_enabled:
            return False

        if source.status == "degraded" and source.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            if source.last_failure_at:
                now = datetime.now(timezone.utc)
                last_fail = source.last_failure_at
                if last_fail.tzinfo is None:
                    last_fail = last_fail.replace(tzinfo=timezone.utc)
                if now - last_fail < timedelta(minutes=COOLDOWN_MINUTES):
                    return False
        return True

    @staticmethod
    async def record_success(session: AsyncSession, source_key: str) -> None:
        """Async records successful poll."""
        now = datetime.now(timezone.utc)
        await session.execute(
            update(DataSource)
            .where(DataSource.source_key == source_key)
            .values(
                status="healthy",
                consecutive_failures=0,
                last_success_at=now,
                updated_at=now,
            )
        )
        await session.commit()
        logger.info("circuit_breaker_healthy", source_key=source_key)

    @staticmethod
    async def record_failure(
        session: AsyncSession, source_key: str, error_message: str | None = None
    ) -> None:
        """Async records poll failure."""
        res = await session.execute(
            select(DataSource).where(DataSource.source_key == source_key)
        )
        source = res.scalar_one_or_none()
        if not source:
            return

        new_failures = source.consecutive_failures + 1
        new_status = "degraded" if new_failures >= MAX_CONSECUTIVE_FAILURES else source.status
        now = datetime.now(timezone.utc)

        source.consecutive_failures = new_failures
        source.status = new_status
        source.last_failure_at = now
        await session.commit()

        logger.warning(
            "circuit_breaker_failure_recorded",
            source_key=source_key,
            consecutive_failures=new_failures,
            status=new_status,
            error=error_message,
        )
