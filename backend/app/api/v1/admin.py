"""
/v1/admin — Platform administration endpoints for Data Sources and DLQ.
Architecture reference: §N.2, §20.
Permissions: require_permission("admin:read") and require_permission("admin:write").
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.db.session import get_db
from app.modules.admin.schemas import (
    DataSourceOut,
    DataSourceUpdateIn,
    DLQEntryOut,
    DLQReplayResponse,
)
from app.modules.events.models import DataSource, DeadLetterQueue
from ingestion.pipeline.pipeline import IngestionPipeline

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/data-sources",
    response_model=list[DataSourceOut],
    summary="List all data source connectors and their health status",
)
async def list_data_sources(
    current_user: CurrentUser = Depends(require_permission("admin:read")),
    db: AsyncSession = Depends(get_db),
) -> list[DataSourceOut]:
    res = await db.execute(select(DataSource).order_by(DataSource.source_key))
    sources = res.scalars().all()
    return [DataSourceOut.model_validate(s) for s in sources]


@router.get(
    "/data-sources/{id}",
    response_model=DataSourceOut,
    summary="Get single data source connector details",
)
async def get_data_source(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin:read")),
    db: AsyncSession = Depends(get_db),
) -> DataSourceOut:
    res = await db.execute(select(DataSource).where(DataSource.id == id))
    source = res.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
    return DataSourceOut.model_validate(source)


@router.patch(
    "/data-sources/{id}",
    response_model=DataSourceOut,
    summary="Update data source configuration or status",
)
async def update_data_source(
    id: uuid.UUID,
    payload: DataSourceUpdateIn,
    current_user: CurrentUser = Depends(require_permission("admin:write")),
    db: AsyncSession = Depends(get_db),
) -> DataSourceOut:
    res = await db.execute(select(DataSource).where(DataSource.id == id))
    source = res.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(source, field, val)

    await db.commit()
    await db.refresh(source)
    return DataSourceOut.model_validate(source)


@router.post(
    "/data-sources/{id}/poll",
    response_model=dict[str, Any],
    summary="Trigger immediate poll for a data source",
)
async def poll_data_source_now(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin:write")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    res = await db.execute(select(DataSource).where(DataSource.id == id))
    source = res.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    pipeline = IngestionPipeline()
    summary = await pipeline.run_async(session=db, connector=source.source_key, force=True)

    return {
        "source_key": summary.source_key,
        "total_fetched": summary.total_fetched,
        "new_records": summary.new_records,
        "duplicates": summary.duplicates,
        "revisions": summary.revisions,
        "next_cursor": summary.next_cursor,
    }


@router.get(
    "/dlq",
    response_model=list[DLQEntryOut],
    summary="List dead letter queue entries",
)
async def list_dlq_entries(
    status_filter: str | None = Query(None, alias="status", description="Filter by status (failed/replayed)"),
    current_user: CurrentUser = Depends(require_permission("admin:read")),
    db: AsyncSession = Depends(get_db),
) -> list[DLQEntryOut]:
    stmt = select(DeadLetterQueue).order_by(DeadLetterQueue.created_at.desc())
    if status_filter:
        stmt = stmt.where(DeadLetterQueue.status == status_filter)

    res = await db.execute(stmt)
    entries = res.scalars().all()
    return [DLQEntryOut.model_validate(e) for e in entries]


@router.post(
    "/dlq/{id}/replay",
    response_model=DLQReplayResponse,
    summary="Replay a failed job from the dead letter queue",
)
async def replay_dlq_entry(
    id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("admin:write")),
    db: AsyncSession = Depends(get_db),
) -> DLQReplayResponse:
    from workers.tasks.ingest import replay_dlq_task

    res = await db.execute(select(DeadLetterQueue).where(DeadLetterQueue.id == id))
    entry = res.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")

    # Execute replay
    result = replay_dlq_task(dlq_id=str(id), replayed_by=current_user.user_id)

    return DLQReplayResponse(
        dlq_id=str(id),
        status="replayed",
        message="Task replayed successfully",
        source_key=result.get("source_key"),
    )
