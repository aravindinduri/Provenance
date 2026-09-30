"""
tests/unit/test_phase4_schemas.py — Unit tests for Phase 4 schemas and validation constraints.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.modules.companies.repository import normalize_company_name
from app.modules.companies.schemas import (
    CompanyCreate,
)
from app.modules.graph.schemas import (
    RelationshipCreate,
    SupplierCreate,
    SupplierUpdate,
)


# ── Company normalization & schemas ──────────────────────────────────────────

def test_normalize_company_name():
    assert normalize_company_name("Acme Corp., Inc.") == "acme corp inc"
    assert normalize_company_name("  HENAN   YIXIN  ALLOYS  ") == "henan yixin alloys"
    assert normalize_company_name("Éxample & Sons") == "example sons"


def test_company_create_validation():
    # Valid
    c = CompanyCreate(legal_name="Acme Corp", country="de")
    assert c.country == "DE"

    # Missing legal name
    with pytest.raises(ValidationError):
        CompanyCreate(legal_name="")

    # Invalid country length
    with pytest.raises(ValidationError):
        CompanyCreate(legal_name="Acme", country="USA")


# ── Supplier schemas & validation ────────────────────────────────────────────

def test_supplier_create_requires_company_id_or_legal_name():
    # Valid with company_id
    cid = uuid.uuid4()
    s1 = SupplierCreate(company_id=cid, criticality=4)
    assert s1.company_id == cid
    assert s1.criticality == 4

    # Valid with legal_name
    s2 = SupplierCreate(legal_name="New Supplier Co", country="in", annual_spend_usd=150000.0)
    assert s2.legal_name == "New Supplier Co"
    assert s2.country == "IN"
    assert s2.annual_spend_usd == 150000.0

    # Invalid when neither provided
    with pytest.raises(ValidationError, match="Either company_id or legal_name must be provided"):
        SupplierCreate()


def test_supplier_criticality_constraint_1_to_5():
    # Criticality must be between 1 and 5
    with pytest.raises(ValidationError):
        SupplierCreate(legal_name="Test", criticality=0)

    with pytest.raises(ValidationError):
        SupplierCreate(legal_name="Test", criticality=6)

    valid = SupplierCreate(legal_name="Test", criticality=5)
    assert valid.criticality == 5


def test_supplier_spend_non_negative():
    with pytest.raises(ValidationError):
        SupplierCreate(legal_name="Test", annual_spend_usd=-50.0)

    with pytest.raises(ValidationError):
        SupplierUpdate(annual_spend_usd=-1.0)


# ── Relationship schemas & validation ────────────────────────────────────────

def test_relationship_create_requires_target():
    from_id = uuid.uuid4()
    to_id = uuid.uuid4()

    # Valid with to_company_id
    r1 = RelationshipCreate(from_company_id=from_id, to_company_id=to_id)
    assert r1.to_company_id == to_id

    # Valid with to_org_id
    org_id = uuid.uuid4()
    r2 = RelationshipCreate(from_company_id=from_id, to_org_id=org_id)
    assert r2.to_org_id == org_id

    # Invalid without either target
    with pytest.raises(ValidationError, match="Either to_company_id or to_org_id must be provided"):
        RelationshipCreate(from_company_id=from_id)
