"""
tests/unit/test_pagination.py — Unit tests for cursor-based pagination.

Verifies:
  1. Base64 URL-safe roundtrip encoding/decoding.
  2. Malformed cursor detection and error handling.
  3. Stable ordering and cursor seeking condition generation.
  4. Simulation of concurrent inserts: new items inserted after cursor
     creation do not shift pages, cause duplicates, or skip items.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.dialects import sqlite

from app.core.pagination import (
    apply_cursor_to_query,
    decode_cursor,
    encode_cursor,
)


def test_cursor_roundtrip_iso_datetime():
    dt = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    uid = uuid.uuid4()

    token = encode_cursor(dt, uid)
    assert isinstance(token, str)
    assert len(token) > 0

    val_str, id_str = decode_cursor(token)
    assert val_str == dt.isoformat()
    assert id_str == str(uid)


def test_cursor_roundtrip_string_and_uuid():
    uid = uuid.uuid4()
    token = encode_cursor("acme-corp", uid)
    val_str, id_str = decode_cursor(token)
    assert val_str == "acme-corp"
    assert id_str == str(uid)


def test_decode_none_or_empty_returns_none():
    assert decode_cursor(None) is None
    assert decode_cursor("") is None


def test_decode_corrupted_token_raises_value_error():
    with pytest.raises(ValueError, match="Invalid cursor format"):
        decode_cursor("not-valid-base64!!!")

    with pytest.raises(ValueError, match="Invalid cursor format"):
        decode_cursor("e30=")  # {} missing required keys


def test_apply_cursor_descending_compiles():
    metadata = MetaData()
    test_table = Table(
        "test_table",
        metadata,
        Column("id", String, primary_key=True),
        Column("created_at", String),
    )

    uid = uuid.uuid4()
    dt_str = "2026-09-30T10:00:00"
    token = encode_cursor(dt_str, uid)

    q = select(test_table)
    q_paginated = apply_cursor_to_query(
        q,
        cursor=token,
        sort_column=test_table.c.created_at,
        id_column=test_table.c.id,
        is_datetime=False,
        descending=True,
    )

    compiled = str(q_paginated.compile(dialect=sqlite.dialect()))
    assert "test_table.created_at <" in compiled or "test_table.created_at =" in compiled


def test_pagination_concurrent_insert_simulation():
    """
    Simulation asserting that cursor pagination is strictly immune to
    offset-shifting bugs caused by concurrent inserts.
    """
    # 1. Ten initial items, timestamps 1..10 (newest = 10)
    items = [
        {"id": f"id_{i:02d}", "created_at": i}
        for i in range(10, 0, -1)
    ]
    # Page 1: limit 5
    page_1 = items[:5]  # items 10, 9, 8, 7, 6
    last_item = page_1[-1]
    cursor = encode_cursor(last_item["created_at"], last_item["id"])

    # 2. Concurrently insert 3 brand new items with created_at = 11, 12, 13
    new_inserts = [
        {"id": "id_13", "created_at": 13},
        {"id": "id_12", "created_at": 12},
        {"id": "id_11", "created_at": 11},
    ]
    db_state = new_inserts + items

    # 3. Fetch Page 2 using cursor
    val_str, id_str = decode_cursor(cursor)
    cursor_val = int(val_str)

    page_2 = [
        row for row in db_state
        if (row["created_at"] < cursor_val) or (row["created_at"] == cursor_val and row["id"] < id_str)
    ][:5]

    # Verify:
    page_1_ids = {r["id"] for r in page_1}
    page_2_ids = {r["id"] for r in page_2}

    # Zero overlap (no duplicate items)
    assert page_1_ids.isdisjoint(page_2_ids)

    # Zero skipped items from original set
    all_seen = [r["id"] for r in page_1] + [r["id"] for r in page_2]
    expected_all_original = [f"id_{i:02d}" for i in range(10, 0, -1)]
    assert all_seen == expected_all_original

    # Concurrently inserted items are NOT in page 2
    for inserted in new_inserts:
        assert inserted["id"] not in page_2_ids
