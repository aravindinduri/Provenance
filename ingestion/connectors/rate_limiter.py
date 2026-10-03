"""
Global rate limiting and token bucket for ingestion connectors.
Architecture reference: §E.1 #3, §F.4 (GDELT global token bucket at 6s spacing & 429 cooldown).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RateLimitCooldownError(Exception):
    """Raised when a connector is in 429 cooldown period."""

    def __init__(self, key: str, remaining_seconds: float):
        self.key = key
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Rate limiter for {key!r} is in cooldown for {remaining_seconds:.1f}s"
        )


class TokenBucketRateLimiter:
    """
    Enforces minimum spacing between requests across workers.
    Backed by Redis if available; uses in-memory tracker as fallback.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self.redis = redis_client
        self._memory_timestamps: dict[str, float] = {}
        self._memory_cooldowns: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def is_in_cooldown(self, key: str) -> tuple[bool, float]:
        """
        Check if the key is currently cooling down after a 429.
        Returns (in_cooldown, remaining_seconds).
        """
        now = time.time()
        cooldown_key = f"provenance:ratelimit:{key}:cooldown"

        if self.redis is not None:
            try:
                ttl = await self.redis.ttl(cooldown_key)
                if ttl and ttl > 0:
                    return True, float(ttl)
                return False, 0.0
            except Exception as exc:
                logger.warning("redis_ratelimit_error", error=str(exc))

        # In-memory fallback
        cooldown_until = self._memory_cooldowns.get(key, 0.0)
        if cooldown_until > now:
            return True, cooldown_until - now
        return False, 0.0

    async def record_429(self, key: str, cooldown_seconds: float = 30.0) -> None:
        """
        Record that a 429 was received. Freezes requests for cooldown_seconds.
        """
        now = time.time()
        logger.warning(
            "rate_limit_429_received",
            key=key,
            cooldown_seconds=cooldown_seconds,
        )
        cooldown_key = f"provenance:ratelimit:{key}:cooldown"

        if self.redis is not None:
            try:
                await self.redis.set(cooldown_key, str(now + cooldown_seconds), ex=int(cooldown_seconds))
                return
            except Exception as exc:
                logger.warning("redis_record_429_error", error=str(exc))

        self._memory_cooldowns[key] = now + cooldown_seconds

    async def acquire(
        self,
        key: str,
        min_interval_seconds: float = 6.0,
        fail_fast: bool = False,
    ) -> float:
        """
        Ensures at least `min_interval_seconds` have passed since the last request.
        If fail_fast is True and spacing would require waiting, raises RateLimitCooldownError.
        Returns the seconds waited.
        """
        in_cooldown, remaining = await self.is_in_cooldown(key)
        if in_cooldown:
            if fail_fast:
                raise RateLimitCooldownError(key, remaining)
            logger.info("waiting_for_cooldown", key=key, remaining=remaining)
            await asyncio.sleep(remaining)

        ts_key = f"provenance:ratelimit:{key}:last_ts"
        now = time.time()
        waited = 0.0

        if self.redis is not None:
            try:
                # Use Redis atomic set with NX or check timestamp
                last_ts_str = await self.redis.get(ts_key)
                if last_ts_str is not None:
                    last_ts = float(last_ts_str)
                    elapsed = now - last_ts
                    if elapsed < min_interval_seconds:
                        delay = min_interval_seconds - elapsed
                        if fail_fast:
                            raise RateLimitCooldownError(key, delay)
                        logger.info("rate_limiter_spacing", key=key, delay_seconds=delay)
                        await asyncio.sleep(delay)
                        waited = delay
                now = time.time()
                await self.redis.set(ts_key, str(now), ex=int(min_interval_seconds * 10))
                return waited
            except RateLimitCooldownError:
                raise
            except Exception as exc:
                logger.warning("redis_acquire_error", error=str(exc))

        # Thread-safe in-memory fallback
        async with self._lock:
            last_ts = self._memory_timestamps.get(key, 0.0)
            elapsed = now - last_ts
            if elapsed < min_interval_seconds:
                delay = min_interval_seconds - elapsed
                if fail_fast:
                    raise RateLimitCooldownError(key, delay)
                await asyncio.sleep(delay)
                waited = delay

            self._memory_timestamps[key] = time.time()
            return waited


# Global singleton instance
_global_limiter: TokenBucketRateLimiter | None = None


def get_token_bucket_limiter() -> TokenBucketRateLimiter:
    global _global_limiter
    if _global_limiter is None:
        try:
            from app.db.redis import get_redis
            client = get_redis()
            _global_limiter = TokenBucketRateLimiter(redis_client=client)
        except Exception:
            _global_limiter = TokenBucketRateLimiter()
    return _global_limiter
