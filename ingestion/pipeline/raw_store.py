"""
RawStore: S3-backed storage for raw ingested payloads with local/memory fallback.
Architecture reference: §D.1, §F.1, §M (source_records.raw_s3_key).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class RawStore:
    """
    Archives raw ingested payloads to S3 (or in-memory/local storage for dev/testing).
    Generates deterministic, partition-friendly S3 keys:
    raw/{source_id}/{YYYY-MM-DD}/{content_hash}.json
    """

    def __init__(self, s3_client: Any | None = None, bucket_name: str | None = None) -> None:
        settings = get_settings()
        self.bucket = bucket_name or settings.s3_bucket_raw_payloads
        self.s3_client = s3_client
        # In-memory storage dictionary used when running offline or in tests without AWS
        self._memory_store: dict[str, str] = {}

    def generate_s3_key(
        self,
        source_id: str,
        content_hash: str,
        extension: str = "json",
        date_str: str | None = None,
    ) -> str:
        """Generates a partition-friendly S3 key."""
        d = date_str or datetime.now().strftime("%Y-%m-%d")
        return f"raw/{source_id}/{d}/{content_hash}.{extension}"

    async def store(
        self,
        source_id: str,
        content_hash: str,
        payload: dict[str, Any] | str | bytes,
        extension: str = "json",
    ) -> str:
        """
        Stores payload and returns the raw_s3_key.
        """
        key = self.generate_s3_key(source_id, content_hash, extension=extension)

        if isinstance(payload, bytes):
            body = payload
            body_str = payload.decode("utf-8", errors="replace")
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
            body_str = payload
        else:
            body_str = json.dumps(payload, default=str)
            body = body_str.encode("utf-8")

        # If live s3_client is provided, upload to AWS S3
        if self.s3_client is not None:
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=body,
                    ContentType="application/json" if extension == "json" else "text/plain",
                )
                return key
            except Exception as exc:
                logger.warning("s3_upload_failed_using_local", key=key, error=str(exc))

        # In-memory / local storage fallback
        self._memory_store[key] = body_str
        return key

    async def get(self, raw_s3_key: str) -> str | None:
        """Retrieves raw payload by S3 key."""
        if self.s3_client is not None:
            try:
                resp = self.s3_client.get_object(Bucket=self.bucket, Key=raw_s3_key)
                return resp["Body"].read().decode("utf-8")
            except Exception as exc:
                logger.warning("s3_get_failed_fallback_memory", key=raw_s3_key, error=str(exc))

        return self._memory_store.get(raw_s3_key)


# Global singleton instance
_raw_store: RawStore | None = None


def get_raw_store() -> RawStore:
    global _raw_store
    if _raw_store is None:
        _raw_store = RawStore()
    return _raw_store
