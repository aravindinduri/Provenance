"""
Cached snapshots connector for offline/cached snapshot sources (MOFCOM, ARECOMS).
Architecture reference: §15, §23 (line 1719), source_type='cached'.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ingestion.connectors.base import FetchResult, NormalizedRecord, SourceConnector
from ingestion.connectors.utils import compute_content_hash


class CachedSnapshotsConnector(SourceConnector):
    """
    Cached snapshots connector for sources without public live APIs (e.g. MOFCOM notices).
    Loads verified snapshot files with source_type='cached'.
    """

    source_id: str = "cached_snapshots"
    source_type: str = "cached_snapshot"
    reliability: str = "medium"

    def __init__(self, snapshot_records: list[dict[str, Any]] | None = None) -> None:
        self.snapshot_records = snapshot_records or []

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """Returns loaded snapshot records."""
        return FetchResult(
            items=self.snapshot_records,
            next_cursor=None,
            metadata={"count": len(self.snapshot_records), "source_type": "cached"},
        )

    def content_hash(self, raw: dict[str, Any]) -> str:
        """Stable sha256 over snapshot record."""
        identity = {
            "id": raw.get("id"),
            "title": (raw.get("title") or "").strip().lower(),
            "source": raw.get("source"),
            "published_date": raw.get("published_date"),
        }
        return compute_content_hash(identity)

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """Pure normalization of cached snapshot record."""
        ext_id = str(raw.get("id", "")).strip()
        title = str(raw.get("title", "")).strip()

        pub_date = None
        p_str = raw.get("published_date")
        if p_str:
            try:
                pub_date = datetime.strptime(str(p_str)[:10], "%Y-%m-%d").date()
            except Exception:
                pass

        chash = self.content_hash(raw)

        return NormalizedRecord(
            source_id=self.source_id,
            external_id=ext_id or f"snap-{chash[:16]}",
            content_hash=chash,
            canonical_url=raw.get("url"),
            title=f"Snapshot [{raw.get('source', 'Archive')}]: {title}",
            published_date=pub_date,
            source_type="cached",
            reliability="medium",
            language=raw.get("language", "zh"),
            raw_payload=raw,
            normalized_data=raw,
        )
