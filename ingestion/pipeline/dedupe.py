"""
Ingestion deduplication, idempotency, and revision tracking.
Architecture reference: §F.3 (Three-layer dedupe and revision detection).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.modules.events.models import SourceRecord, SourceRecordVersion
from ingestion.connectors.base import NormalizedRecord

logger = structlog.get_logger(__name__)


@dataclass
class DedupeResult:
    source_record_id: uuid.UUID
    is_new: bool
    is_duplicate: bool
    is_revision: bool
    seen_count: int
    version: int = 1


def process_and_dedupe_record_sync(
    session: Session,
    source_db_id: uuid.UUID,
    normalized: NormalizedRecord,
    raw_s3_key: str,
) -> DedupeResult:
    """
    Synchronous processing of a normalized record against DB idempotency rules:
      1. UNIQUE (source_id, external_id)
      2. UNIQUE (source_id, content_hash)
      3. Revision detection: same external_id, different content_hash -> new version
    """
    now = datetime.now(timezone.utc)
    ext_id = normalized.external_id
    chash = normalized.content_hash

    existing_record: SourceRecord | None = None

    # Layer 1: Check by external_id if present
    if ext_id:
        existing_record = session.execute(
            select(SourceRecord).where(
                SourceRecord.source_id == source_db_id,
                SourceRecord.external_id == ext_id,
            )
        ).scalar_one_or_none()

    # Layer 2: Check by content_hash if not found by external_id
    if not existing_record:
        existing_record = session.execute(
            select(SourceRecord).where(
                SourceRecord.source_id == source_db_id,
                SourceRecord.content_hash == chash,
            )
        ).scalar_one_or_none()

    # Scenario A: Record already exists
    if existing_record:
        # Check if content has changed (revision detected)
        if existing_record.content_hash != chash:
            # Query current max version
            max_ver_result = session.execute(
                select(func.coalesce(func.max(SourceRecordVersion.version), 1)).where(
                    SourceRecordVersion.source_record_id == existing_record.id
                )
            ).scalar_one()
            next_version = max_ver_result + 1

            # Snapshot previous state into source_record_versions
            version_entry = SourceRecordVersion(
                id=uuid.uuid4(),
                source_record_id=existing_record.id,
                version=next_version,
                content_hash=existing_record.content_hash,
                normalized=existing_record.normalized,
                raw_s3_key=existing_record.raw_s3_key,
                detected_at=now,
            )
            session.add(version_entry)

            # Update current record with new revision
            existing_record.content_hash = chash
            existing_record.normalized = normalized.normalized_data
            existing_record.raw_s3_key = raw_s3_key
            existing_record.title = normalized.title
            existing_record.published_date = normalized.published_date
            existing_record.canonical_url = normalized.canonical_url
            existing_record.seen_count += 1
            existing_record.last_seen_at = now
            existing_record.updated_at = now

            session.commit()
            session.refresh(existing_record)

            logger.info(
                "source_record_revised",
                source_record_id=str(existing_record.id),
                version=next_version,
                external_id=ext_id,
            )
            return DedupeResult(
                source_record_id=existing_record.id,
                is_new=False,
                is_duplicate=False,
                is_revision=True,
                seen_count=existing_record.seen_count,
                version=next_version,
            )

        # Same content -> duplicate re-fetch
        existing_record.seen_count += 1
        existing_record.last_seen_at = now
        existing_record.updated_at = now
        session.commit()
        session.refresh(existing_record)

        return DedupeResult(
            source_record_id=existing_record.id,
            is_new=False,
            is_duplicate=True,
            is_revision=False,
            seen_count=existing_record.seen_count,
            version=1,
        )

    # Scenario B: Brand new record
    new_record = SourceRecord(
        id=uuid.uuid4(),
        source_id=source_db_id,
        external_id=ext_id,
        content_hash=chash,
        canonical_url=normalized.canonical_url,
        title=normalized.title,
        published_date=normalized.published_date,
        retrieved_at=now,
        raw_s3_key=raw_s3_key,
        normalized=normalized.normalized_data,
        source_type=normalized.source_type,
        reliability=normalized.reliability,
        language=normalized.language,
        processing_status="pending",
        seen_count=1,
        last_seen_at=now,
    )
    session.add(new_record)
    session.commit()
    session.refresh(new_record)

    logger.info(
        "source_record_created",
        source_record_id=str(new_record.id),
        external_id=ext_id,
        source_id=str(source_db_id),
    )
    return DedupeResult(
        source_record_id=new_record.id,
        is_new=True,
        is_duplicate=False,
        is_revision=False,
        seen_count=1,
        version=1,
    )


async def process_and_dedupe_record_async(
    session: AsyncSession,
    source_db_id: uuid.UUID,
    normalized: NormalizedRecord,
    raw_s3_key: str,
) -> DedupeResult:
    """
    Asynchronous version of process_and_dedupe_record.
    """
    now = datetime.now(timezone.utc)
    ext_id = normalized.external_id
    chash = normalized.content_hash

    existing_record: SourceRecord | None = None

    if ext_id:
        res = await session.execute(
            select(SourceRecord).where(
                SourceRecord.source_id == source_db_id,
                SourceRecord.external_id == ext_id,
            )
        )
        existing_record = res.scalar_one_or_none()

    if not existing_record:
        res = await session.execute(
            select(SourceRecord).where(
                SourceRecord.source_id == source_db_id,
                SourceRecord.content_hash == chash,
            )
        )
        existing_record = res.scalar_one_or_none()

    if existing_record:
        if existing_record.content_hash != chash:
            res_ver = await session.execute(
                select(func.coalesce(func.max(SourceRecordVersion.version), 1)).where(
                    SourceRecordVersion.source_record_id == existing_record.id
                )
            )
            next_version = res_ver.scalar_one() + 1

            version_entry = SourceRecordVersion(
                id=uuid.uuid4(),
                source_record_id=existing_record.id,
                version=next_version,
                content_hash=existing_record.content_hash,
                normalized=existing_record.normalized,
                raw_s3_key=existing_record.raw_s3_key,
                detected_at=now,
            )
            session.add(version_entry)

            existing_record.content_hash = chash
            existing_record.normalized = normalized.normalized_data
            existing_record.raw_s3_key = raw_s3_key
            existing_record.title = normalized.title
            existing_record.published_date = normalized.published_date
            existing_record.canonical_url = normalized.canonical_url
            existing_record.seen_count += 1
            existing_record.last_seen_at = now
            existing_record.updated_at = now

            await session.commit()
            await session.refresh(existing_record)

            return DedupeResult(
                source_record_id=existing_record.id,
                is_new=False,
                is_duplicate=False,
                is_revision=True,
                seen_count=existing_record.seen_count,
                version=next_version,
            )

        existing_record.seen_count += 1
        existing_record.last_seen_at = now
        existing_record.updated_at = now
        await session.commit()
        await session.refresh(existing_record)

        return DedupeResult(
            source_record_id=existing_record.id,
            is_new=False,
            is_duplicate=True,
            is_revision=False,
            seen_count=existing_record.seen_count,
            version=1,
        )

    new_record = SourceRecord(
        id=uuid.uuid4(),
        source_id=source_db_id,
        external_id=ext_id,
        content_hash=chash,
        canonical_url=normalized.canonical_url,
        title=normalized.title,
        published_date=normalized.published_date,
        retrieved_at=now,
        raw_s3_key=raw_s3_key,
        normalized=normalized.normalized_data,
        source_type=normalized.source_type,
        reliability=normalized.reliability,
        language=normalized.language,
        processing_status="pending",
        seen_count=1,
        last_seen_at=now,
    )
    session.add(new_record)
    await session.commit()
    await session.refresh(new_record)

    return DedupeResult(
        source_record_id=new_record.id,
        is_new=True,
        is_duplicate=False,
        is_revision=False,
        seen_count=1,
        version=1,
    )
