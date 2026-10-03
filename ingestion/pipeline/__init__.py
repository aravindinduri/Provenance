"""
Pipeline package exports.
"""

from ingestion.pipeline.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
)
from ingestion.pipeline.dedupe import (
    DedupeResult,
    process_and_dedupe_record_async,
    process_and_dedupe_record_sync,
)
from ingestion.pipeline.pipeline import IngestionPipeline, IngestionSummary
from ingestion.pipeline.raw_store import RawStore, get_raw_store

__all__ = [
    "RawStore",
    "get_raw_store",
    "CircuitBreaker",
    "CircuitBreakerOpenException",
    "DedupeResult",
    "process_and_dedupe_record_sync",
    "process_and_dedupe_record_async",
    "IngestionPipeline",
    "IngestionSummary",
]
