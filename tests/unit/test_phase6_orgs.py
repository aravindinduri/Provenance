"""
tests/unit/test_phase6_orgs.py — Unit tests for Phase 6 organization updates and onboarding status.
"""

import uuid
from app.modules.organizations.schemas import OrganizationUpdate


def test_organization_update_accepts_company_id():
    cid = uuid.uuid4()
    payload = OrganizationUpdate(name="Acme Global", company_id=cid)
    assert payload.company_id == cid
    assert payload.name == "Acme Global"


def test_organization_update_accepts_onboarding_completed():
    payload = OrganizationUpdate(onboarding_completed=True)
    assert payload.onboarding_completed is True

    payload_false = OrganizationUpdate(onboarding_completed=False)
    assert payload_false.onboarding_completed is False


def test_organization_update_country_normalization():
    payload = OrganizationUpdate(country="us")
    assert payload.country == "US"
