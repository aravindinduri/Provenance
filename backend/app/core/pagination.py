"""
app/core/pagination.py — Cursor-based pagination for API endpoints.

Per arch §N.1: Offset pagination is rejected — alert and supplier lists change
constantly under concurrent inserts, and offset causes skipped/duplicated rows.
Cursor pagination provides stable windows by seeking relative to the last-seen
(sort_value, id) tuple.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, or_

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata describing the pagination state."""

    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor token to pass to ?cursor= to fetch the next page",
    )
    has_more: bool = Field(
        default=False,
        description="True if there are more records beyond this page",
    )
    total: int | None = Field(
        default=None,
        description="Optional total count of matching records across all pages",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard container for paginated API responses."""

    data: list[T]
    pagination: PaginationMeta


def encode_cursor(sort_value: Any, id_value: uuid.UUID | str) -> str:
    """Encode sort_value and id_value into an opaque, URL-safe base64 string."""
    if isinstance(sort_value, datetime | date):
        val_str = sort_value.isoformat()
    else:
        val_str = str(sort_value)

    payload = {
        "v": val_str,
        "id": str(id_value),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    """
    Decode an opaque cursor token into (sort_value_str, id_str).
    Returns None if cursor is None or empty.
    Raises ValueError if cursor is malformed.
    """
    if not cursor:
        return None

    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        val_str = payload["v"]
        id_str = payload["id"]
        return val_str, id_str
    except Exception as exc:
        raise ValueError(f"Invalid cursor format: {cursor}") from exc


def apply_cursor_to_query(
    query: Select,
    *,
    cursor: str | None,
    sort_column: Any,
    id_column: Any,
    is_datetime: bool = False,
    descending: bool = True,
) -> Select:
    """
    Apply cursor-seeking filter to a SQLAlchemy SELECT statement.

    For descending order (newest first):
      WHERE (sort_col < cursor_val) OR (sort_col == cursor_val AND id_col < cursor_id)
    For ascending order:
      WHERE (sort_col > cursor_val) OR (sort_col == cursor_val AND id_col > cursor_id)
    """
    decoded = decode_cursor(cursor)
    if not decoded:
        return query

    raw_val, id_str = decoded
    val: Any
    if is_datetime:
        val = datetime.fromisoformat(raw_val)
    else:
        val = raw_val

    try:
        target_id: Any = uuid.UUID(id_str)
    except ValueError:
        target_id = id_str

    if descending:
        condition = or_(
            sort_column < val,
            and_(sort_column == val, id_column < target_id),
        )
    else:
        condition = or_(
            sort_column > val,
            and_(sort_column == val, id_column > target_id),
        )

    return query.where(condition)
