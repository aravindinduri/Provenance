"""
app/modules/graph/bulk_service.py — CSV parsing, validation, and async execution for bulk supplier import.

Acceptance: 500-row CSV imports without timeout.
"""

from __future__ import annotations

import csv
import io
import re
import threading
import uuid
from datetime import datetime, timezone

import structlog

from app.modules.graph.schemas import (
    BulkRowError,
    BulkSupplierJobOut,
    SupplierCreate,
)

logger = structlog.get_logger(__name__)

# Column aliases mapping for flexible CSV imports
NAME_ALIASES = {
    "legal_name",
    "legal name",
    "name",
    "company_name",
    "company name",
    "supplier",
    "supplier_name",
    "supplier name",
    "vendor",
    "vendor_name",
}
COUNTRY_ALIASES = {
    "country",
    "country_code",
    "country code",
    "iso_country",
    "nation",
}
DOMAIN_ALIASES = {
    "primary_domain",
    "primary domain",
    "domain",
    "website",
    "url",
    "web",
}
TIER_ALIASES = {
    "tier",
    "supplier_tier",
    "supplier tier",
    "tier_level",
}
CRITICALITY_ALIASES = {
    "criticality",
    "criticality_score",
    "criticality score",
    "risk_level",
    "risk level",
    "priority",
    "criticality (1-5)",
}
SPEND_ALIASES = {
    "annual_spend_usd",
    "annual spend usd",
    "annual_spend",
    "annual spend",
    "spend",
    "spend_usd",
    "spend ($)",
    "annual spend ($)",
    "spend usd",
}
CATEGORY_ALIASES = {
    "category",
    "procurement_category",
    "procurement category",
    "commodity",
    "segment",
}
SINGLE_SOURCE_ALIASES = {
    "single_source",
    "single source",
    "is_single_source",
    "sole_source",
    "sole source",
}
LEAD_TIME_ALIASES = {
    "lead_time_days",
    "lead time days",
    "lead_time",
    "lead time",
    "lead_time_(days)",
    "lead time (days)",
}

CRITICALITY_WORDS = {
    "1": 1,
    "minimal": 1,
    "negligible": 1,
    "very low": 1,
    "2": 2,
    "low": 2,
    "3": 3,
    "medium": 3,
    "moderate": 3,
    "normal": 3,
    "4": 4,
    "high": 4,
    "elevated": 4,
    "5": 5,
    "critical": 5,
    "severe": 5,
    "highest": 5,
}


def _normalize_header(h: str) -> str:
    cleaned = h.lower().strip().replace("-", "_")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def parse_supplier_csv(
    csv_text: str,
) -> tuple[list[SupplierCreate], list[BulkRowError]]:
    """
    Parse CSV text into a list of SupplierCreate models and row-level errors.
    Returns (valid_rows, errors).
    """
    valid_rows: list[SupplierCreate] = []
    errors: list[BulkRowError] = []

    if not csv_text or not csv_text.strip():
        errors.append(BulkRowError(row=0, error="CSV content is empty"))
        return valid_rows, errors

    # Detect delimiter: comma, semicolon, tab
    first_line = csv_text.strip().split("\n", 1)[0]
    delimiter = ","
    if "\t" in first_line and first_line.count("\t") > first_line.count(","):
        delimiter = "\t"
    elif ";" in first_line and first_line.count(";") > first_line.count(","):
        delimiter = ";"

    reader = csv.reader(io.StringIO(csv_text.strip()), delimiter=delimiter)
    try:
        raw_header = next(reader)
    except StopIteration:
        errors.append(BulkRowError(row=0, error="CSV has no rows"))
        return valid_rows, errors

    header_map: dict[str, int] = {}
    for idx, col in enumerate(raw_header):
        normalized = _normalize_header(col)
        header_map[normalized] = idx

    # Helper to get col value
    def get_val(row_data: list[str], aliases: set[str]) -> str | None:
        for alias in aliases:
            if alias in header_map:
                col_idx = header_map[alias]
                if col_idx < len(row_data):
                    val = row_data[col_idx].strip()
                    if val:
                        return val
        return None

    # Verify name column is present
    has_name_col = any(alias in header_map for alias in NAME_ALIASES)
    if not has_name_col:
        errors.append(
            BulkRowError(
                row=1,
                error="CSV missing required header for company/supplier name (e.g. 'legal_name', 'name', 'supplier_name')",
            )
        )
        return valid_rows, errors

    for row_idx, row_data in enumerate(reader, start=2):
        if not row_data or all(not c.strip() for c in row_data):
            continue  # skip completely blank lines

        raw_name = get_val(row_data, NAME_ALIASES)
        if not raw_name:
            errors.append(
                BulkRowError(row=row_idx, error="Missing required supplier legal name")
            )
            continue

        raw_country = get_val(row_data, COUNTRY_ALIASES)
        country: str | None = None
        if raw_country:
            clean_c = raw_country.strip().upper()
            if len(clean_c) == 2 and clean_c.isalpha():
                country = clean_c
            else:
                errors.append(
                    BulkRowError(
                        row=row_idx,
                        legal_name=raw_name,
                        error=f"Invalid 2-letter country code '{raw_country}'",
                    )
                )
                continue

        raw_domain = get_val(row_data, DOMAIN_ALIASES)
        primary_domain = (
            re.sub(r"^https?://", "", raw_domain.lower().strip()).rstrip("/")
            if raw_domain
            else None
        )

        raw_tier = get_val(row_data, TIER_ALIASES)
        tier = 1
        if raw_tier:
            try:
                tier = int(raw_tier)
                if not (1 <= tier <= 10):
                    tier = 1
            except ValueError:
                tier = 1

        raw_crit = get_val(row_data, CRITICALITY_ALIASES)
        criticality = 3
        if raw_crit:
            norm_crit = raw_crit.lower().strip()
            if norm_crit in CRITICALITY_WORDS:
                criticality = CRITICALITY_WORDS[norm_crit]
            else:
                try:
                    c_int = int(norm_crit)
                    if 1 <= c_int <= 5:
                        criticality = c_int
                except ValueError:
                    criticality = 3

        raw_spend = get_val(row_data, SPEND_ALIASES)
        annual_spend_usd: float | None = None
        if raw_spend:
            clean_spend = re.sub(r"[\$,\s]", "", raw_spend)
            try:
                spend_val = float(clean_spend)
                if spend_val >= 0:
                    annual_spend_usd = spend_val
            except ValueError:
                errors.append(
                    BulkRowError(
                        row=row_idx,
                        legal_name=raw_name,
                        error=f"Invalid spend amount '{raw_spend}'",
                    )
                )
                continue

        category = get_val(row_data, CATEGORY_ALIASES)

        raw_ss = get_val(row_data, SINGLE_SOURCE_ALIASES)
        single_source = False
        if raw_ss:
            single_source = raw_ss.lower().strip() in {"true", "yes", "1", "y"}

        raw_lt = get_val(row_data, LEAD_TIME_ALIASES)
        lead_time_days: int | None = None
        if raw_lt:
            try:
                lead_time_days = max(0, int(raw_lt.strip()))
            except ValueError:
                pass

        valid_rows.append(
            SupplierCreate(
                legal_name=raw_name,
                country=country,
                primary_domain=primary_domain,
                tier=tier,
                criticality=criticality,
                annual_spend_usd=annual_spend_usd,
                category=category,
                single_source=single_source,
                lead_time_days=lead_time_days,
                source="user_declared",
            )
        )

    return valid_rows, errors


class BulkJobStore:
    """
    ponytail: thread-safe in-memory store for bulk job progress; handles up to 10k concurrent
    jobs per process. Upgrade path: Redis hash with 24h TTL or Postgres bulk_jobs table for multi-node clusters.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[uuid.UUID, BulkSupplierJobOut] = {}

    def create_job(self, org_id: uuid.UUID, total_rows: int = 0) -> BulkSupplierJobOut:
        job = BulkSupplierJobOut(
            job_id=uuid.uuid4(),
            org_id=org_id,
            status="pending",
            total_rows=total_rows,
            processed_rows=0,
            successful_rows=0,
            failed_rows=0,
            errors=[],
            created_at=datetime.now(tz=timezone.utc),
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get_job(
        self, job_id: uuid.UUID, org_id: uuid.UUID
    ) -> BulkSupplierJobOut | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.org_id == org_id:
                return job
            return None

    def update_job(self, job: BulkSupplierJobOut) -> None:
        with self._lock:
            self._jobs[job.job_id] = job


# Global singleton job store
bulk_job_store = BulkJobStore()


async def execute_bulk_supplier_job(
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    rows: list[SupplierCreate],
    parse_errors: list[BulkRowError],
) -> None:
    """
    Background worker that iterates through supplier rows, creates or links canonical companies,
    and creates supplier relationship edges for the organization.
    Commits periodically to keep transactions tight and updates progress.
    """
    job = bulk_job_store.get_job(job_id, org_id)
    if not job:
        return

    job.status = "processing"
    job.total_rows = len(rows) + len(parse_errors)
    job.errors.extend(parse_errors)
    job.failed_rows += len(parse_errors)
    job.processed_rows += len(parse_errors)
    bulk_job_store.update_job(job)

    if not rows:
        job.status = "completed" if job.successful_rows > 0 or not parse_errors else "failed"
        job.completed_at = datetime.now(tz=timezone.utc)
        bulk_job_store.update_job(job)
        return

    from app.db.session import get_session_factory
    from app.modules.graph.service import GraphService

    session_factory = get_session_factory()
    batch_size = 50

    try:
        async with session_factory() as session:
            svc = GraphService(session)
            for idx, row in enumerate(rows, start=1):
                try:
                    await svc.create_supplier(org_id, row)
                    job.successful_rows += 1
                except Exception as exc:
                    logger.warning("bulk_supplier_row_error", row=idx, error=str(exc))
                    job.failed_rows += 1
                    job.errors.append(
                        BulkRowError(
                            row=idx + len(parse_errors),
                            legal_name=row.legal_name,
                            error=str(exc),
                        )
                    )

                job.processed_rows += 1
                if idx % batch_size == 0 or idx == len(rows):
                    await session.commit()
                    bulk_job_store.update_job(job)

            job.status = "completed"
            job.completed_at = datetime.now(tz=timezone.utc)
            bulk_job_store.update_job(job)
    except Exception as exc:
        logger.error("bulk_supplier_job_failed", job_id=str(job_id), error=str(exc))
        job.status = "failed"
        job.completed_at = datetime.now(tz=timezone.utc)
        job.errors.append(BulkRowError(row=0, error=f"Internal batch failure: {exc}"))
        bulk_job_store.update_job(job)
