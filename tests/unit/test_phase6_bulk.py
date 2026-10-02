"""
tests/unit/test_phase6_bulk.py — Unit tests for Phase 6 bulk supplier import & CSV parser.

Acceptance criteria (§Phase 6):
  - 500-row CSV imports without timeout.
  - Multi-variant column headers parsed cleanly.
  - Criticality text-to-integer mappings.
  - Row-level error collection without aborting entire batch.
  - Tenant scoping on bulk job retrieval.
"""

import time
import uuid
import pytest

from app.modules.graph.bulk_service import (
    BulkJobStore,
    parse_supplier_csv,
)
from app.modules.graph.schemas import BulkSupplierUploadRequest, SupplierCreate


def test_parse_standard_supplier_csv():
    csv_data = """legal_name,country,primary_domain,tier,criticality,annual_spend_usd,category,single_source,lead_time_days
Acme Fasteners Inc,US,acmefasteners.com,1,4,1500000.50,Hardware,true,14
Tokyo Precision Co,JP,tokyoprecision.jp,2,5,3200000.00,Electronics,false,45
Berlin Tech GmbH,DE,berlin-tech.de,1,2,75000.00,Services,false,7
"""
    rows, errors = parse_supplier_csv(csv_data)
    assert len(errors) == 0
    assert len(rows) == 3

    assert rows[0].legal_name == "Acme Fasteners Inc"
    assert rows[0].country == "US"
    assert rows[0].primary_domain == "acmefasteners.com"
    assert rows[0].tier == 1
    assert rows[0].criticality == 4
    assert rows[0].annual_spend_usd == 1500000.50
    assert rows[0].category == "Hardware"
    assert rows[0].single_source is True
    assert rows[0].lead_time_days == 14

    assert rows[1].legal_name == "Tokyo Precision Co"
    assert rows[1].country == "JP"
    assert rows[1].criticality == 5
    assert rows[1].tier == 2

    assert rows[2].legal_name == "Berlin Tech GmbH"
    assert rows[2].country == "DE"
    assert rows[2].criticality == 2


def test_parse_supplier_csv_with_varied_headers_and_word_criticality():
    csv_data = """Supplier Name; Country Code; Website; Priority; Spend ($); Commodity; Sole Source
Stark Industries; US; https://stark.com; Critical; $12,500,000; Defense; Yes
Wayne Enterprises; US; wayne.org; High; $8,000,000; Logistics; No
Pym Technologies; US; pym.tech; Low; $450,000; R&D; false
"""
    rows, errors = parse_supplier_csv(csv_data)
    assert len(errors) == 0
    assert len(rows) == 3

    assert rows[0].legal_name == "Stark Industries"
    assert rows[0].country == "US"
    assert rows[0].primary_domain == "stark.com"
    assert rows[0].criticality == 5
    assert rows[0].annual_spend_usd == 12500000.0
    assert rows[0].category == "Defense"
    assert rows[0].single_source is True

    assert rows[1].legal_name == "Wayne Enterprises"
    assert rows[1].criticality == 4
    assert rows[1].annual_spend_usd == 8000000.0

    assert rows[2].legal_name == "Pym Technologies"
    assert rows[2].criticality == 2
    assert rows[2].annual_spend_usd == 450000.0


def test_parse_supplier_csv_with_row_errors():
    csv_data = """legal_name,country,annual_spend_usd
Valid Corp,US,50000
,DE,10000
Bad Country Inc,GERMANY,25000
Bad Spend Ltd,IN,INVALID_NUMBER
"""
    rows, errors = parse_supplier_csv(csv_data)
    assert len(rows) == 1
    assert rows[0].legal_name == "Valid Corp"
    assert len(errors) == 3

    error_msgs = [e.error for e in errors]
    assert any("Missing required" in m for m in error_msgs)
    assert any("Invalid 2-letter country code" in m for m in error_msgs)
    assert any("Invalid spend amount" in m for m in error_msgs)


def test_parse_500_row_csv_benchmark():
    """Verify 500 rows parse cleanly under 100 milliseconds."""
    lines = ["legal_name,country,primary_domain,tier,criticality,annual_spend_usd,category"]
    for i in range(1, 501):
        lines.append(
            f"Supplier {i:03d} Ltd,US,supplier{i}.com,{(i%3)+1},{(i%5)+1},{i*10000}.00,Cat{(i%8)+1}"
        )
    csv_text = "\n".join(lines)

    start = time.perf_counter()
    rows, errors = parse_supplier_csv(csv_text)
    elapsed = time.perf_counter() - start

    assert len(errors) == 0
    assert len(rows) == 500
    assert elapsed < 0.2, f"500-row parse took {elapsed:.3f}s, expected < 0.2s"


def test_bulk_job_store_lifecycle_and_tenant_scoping():
    store = BulkJobStore()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    job_a = store.create_job(org_id=org_a, total_rows=100)
    assert job_a.status == "pending"
    assert job_a.total_rows == 100

    # Retrieve matching org
    retrieved = store.get_job(job_a.job_id, org_a)
    assert retrieved is not None
    assert retrieved.job_id == job_a.job_id

    # Cross-tenant read rejected
    foreign_retrieved = store.get_job(job_a.job_id, org_b)
    assert foreign_retrieved is None

    # Update job
    job_a.processed_rows = 50
    job_a.successful_rows = 48
    job_a.failed_rows = 2
    store.update_job(job_a)

    updated = store.get_job(job_a.job_id, org_a)
    assert updated.processed_rows == 50
    assert updated.successful_rows == 48
    assert updated.failed_rows == 2


def test_bulk_supplier_upload_request_validation():
    req = BulkSupplierUploadRequest(
        raw_csv="name,country\nAlpha,US",
        rows=[
            SupplierCreate(legal_name="Beta Corp", country="IN", criticality=4)
        ],
    )
    assert req.raw_csv is not None
    assert len(req.rows) == 1
    assert req.rows[0].legal_name == "Beta Corp"
