"""
Admin module schemas for data sources, DLQ, and platform oversight.
Architecture reference: §N.2, §20.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_key: str
    name: str
    source_type: str
    base_url: str | None = None
    auth_type: str | None = None
    reliability: str
    is_enabled: bool
    status: str
    poll_interval_seconds: int | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    license_terms: str | None = None
    terms_verified_at: date | None = None
    coverage_notes: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DataSourceUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_enabled: bool | None = None
    poll_interval_seconds: int | None = None
    status: str | None = None
    reliability: str | None = None
    coverage_notes: str | None = None


class DLQEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_name: str
    payload: dict[str, Any]
    error: str | None = None
    traceback: str | None = None
    retry_count: int
    status: str
    created_at: datetime
    replayed_at: datetime | None = None
    replayed_by: str | None = None


class DLQReplayResponse(BaseModel):
    dlq_id: str
    status: str
    message: str
    source_key: str | None = None
