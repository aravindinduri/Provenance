"""
SourceConnector protocol and core ingestion schemas.
Architecture reference: §F.2, §6, Engineering Rule 17 (replaceable providers).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class FetchResult(BaseModel):
    """
    Result returned by connector.fetch().
    MUST contain raw untransformed items and an optional cursor for pagination.
    """

    model_config = ConfigDict(extra="ignore")

    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedRecord(BaseModel):
    """
    Standardized record produced by connector.normalize(raw).
    Pure transformation, independent of DB models and storage.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: str
    external_id: str | None = None
    content_hash: str
    canonical_url: str | None = None
    title: str | None = None
    published_date: date | None = None
    source_type: Literal["live", "cached"] = "live"
    reliability: Literal["high", "medium", "low"] = "high"
    language: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    normalized_data: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class SourceConnector(Protocol):
    """
    Unified contract for all data source connectors.
    Every source implements this protocol.
    """

    source_id: str
    source_type: Literal["api", "bulk_download", "rss", "html_monitor", "cached_snapshot"]
    reliability: Literal["high", "medium", "low"]

    async def fetch(self, cursor: str | None = None) -> FetchResult:
        """
        Fetch raw items from source.
        MUST NOT transform data.
        """
        ...

    def normalize(self, raw: dict[str, Any]) -> NormalizedRecord:
        """
        Pure function: map raw item to common NormalizedRecord schema.
        Contains NO I/O — fully unit-testable against recorded fixtures.
        """
        ...

    def content_hash(self, raw: dict[str, Any]) -> str:
        """
        Compute deterministic SHA-256 hash over identity-bearing fields only.
        """
        ...


@runtime_checkable
class NewsConnector(SourceConnector, Protocol):
    """
    Specialized news provider interface (arch line 532).
    Allows plug-and-play addition of paid news providers (e.g. Factiva, NewsAPI)
    without refactoring ingestion pipeline.
    """

    async def search_news(
        self,
        query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        cursor: str | None = None,
    ) -> FetchResult:
        """Search news articles by query and date bounds."""
        ...
