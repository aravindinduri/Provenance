"""
tests/unit/test_role_matrix.py

Exhaustive role × permission matrix tests.

Every cell of the matrix is explicit: which roles HAVE and DO NOT HAVE each
permission is asserted, not inferred.  This makes accidental privilege
escalation or regression immediately visible as a test failure — a new
permission added to the wrong role will show up here.

Design decision: these tests are deliberately verbose rather than data-driven
so that a failing test names the exact (role, permission) pair that broke.
"""

from __future__ import annotations

import pytest

from app.auth.base import (
    ROLE_ANALYST,
    ROLE_ORG_ADMIN,
    ROLE_ORG_USER,
    ROLE_PLATFORM_ADMIN,
    ROLE_READ_ONLY,
    has_permission,
)

# ---------------------------------------------------------------------------
# Matrix definition
# permission → roles that SHOULD have it (others must NOT)
# ---------------------------------------------------------------------------

_SHOULD_HAVE: dict[str, set[str]] = {
    # Platform-only
    "platform:read": {ROLE_PLATFORM_ADMIN},
    "platform:write": {ROLE_PLATFORM_ADMIN},
    "admin:read": {ROLE_PLATFORM_ADMIN},
    "admin:write": {ROLE_PLATFORM_ADMIN},
    # Org-level reads — everyone in an org
    "org:read": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER, ROLE_READ_ONLY},
    "members:read": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER, ROLE_READ_ONLY},
    "suppliers:read": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER, ROLE_READ_ONLY},
    "alerts:read": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER, ROLE_READ_ONLY},
    "documents:read": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER, ROLE_READ_ONLY},
    "graph:read": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER, ROLE_READ_ONLY},
    # Org writes — not read_only, not org_user (except alerts)
    "org:write": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN},
    "members:write": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN},
    "suppliers:write": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST},
    "alerts:write": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST, ROLE_ORG_USER},
    "documents:write": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST},
    "graph:write": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST},
    "ai:use": {ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_ANALYST},
}

_ALL_ROLES = {
    ROLE_PLATFORM_ADMIN,
    ROLE_ORG_ADMIN,
    ROLE_ANALYST,
    ROLE_ORG_USER,
    ROLE_READ_ONLY,
}


# ---------------------------------------------------------------------------
# Positive: every role in _SHOULD_HAVE[perm] must have that permission
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "permission,role",
    [
        (perm, role)
        for perm, roles in _SHOULD_HAVE.items()
        for role in roles
    ],
    ids=lambda x: x,
)
def test_role_has_permission(permission: str, role: str) -> None:
    assert has_permission(role, permission), (
        f"Role '{role}' should have permission '{permission}' but does not"
    )


# ---------------------------------------------------------------------------
# Negative: every role NOT in _SHOULD_HAVE[perm] must NOT have that permission
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "permission,role",
    [
        (perm, role)
        for perm, should_roles in _SHOULD_HAVE.items()
        for role in (_ALL_ROLES - should_roles)
    ],
    ids=lambda x: x,
)
def test_role_does_not_have_permission(permission: str, role: str) -> None:
    assert not has_permission(role, permission), (
        f"Role '{role}' must NOT have permission '{permission}' but does"
    )


# ---------------------------------------------------------------------------
# Structural: platform_admin is a strict superset of org_admin
# ---------------------------------------------------------------------------

class TestRoleHierarchy:
    def test_platform_admin_is_superset_of_org_admin(self) -> None:
        from app.auth.base import PERMISSIONS
        org_admin_perms = PERMISSIONS[ROLE_ORG_ADMIN]
        platform_perms = PERMISSIONS[ROLE_PLATFORM_ADMIN]
        missing = org_admin_perms - platform_perms
        assert not missing, (
            f"platform_admin is missing org_admin permissions: {missing}"
        )

    def test_org_admin_is_superset_of_analyst(self) -> None:
        from app.auth.base import PERMISSIONS
        analyst_perms = PERMISSIONS[ROLE_ANALYST]
        org_admin_perms = PERMISSIONS[ROLE_ORG_ADMIN]
        missing = analyst_perms - org_admin_perms
        assert not missing, (
            f"org_admin is missing analyst permissions: {missing}"
        )

    def test_analyst_is_superset_of_read_only(self) -> None:
        from app.auth.base import PERMISSIONS
        read_only_perms = PERMISSIONS[ROLE_READ_ONLY]
        analyst_perms = PERMISSIONS[ROLE_ANALYST]
        missing = read_only_perms - analyst_perms
        assert not missing, (
            f"analyst is missing read_only permissions: {missing}"
        )

    def test_no_role_has_zero_permissions(self) -> None:
        from app.auth.base import PERMISSIONS
        for role, perms in PERMISSIONS.items():
            assert len(perms) > 0, f"Role '{role}' has no permissions defined"

    def test_all_defined_roles_are_in_permissions_dict(self) -> None:
        from app.auth.base import PERMISSIONS
        for role in _ALL_ROLES:
            assert role in PERMISSIONS, f"Role '{role}' missing from PERMISSIONS dict"


# ---------------------------------------------------------------------------
# CurrentUser.has_permission delegates correctly
# ---------------------------------------------------------------------------

class TestCurrentUserHasPermission:
    def test_analyst_can_write_suppliers(self) -> None:
        from app.auth.base import CurrentUser
        u = CurrentUser(
            user_id="u", org_id="o", clerk_org_id="c", role=ROLE_ANALYST
        )
        assert u.has_permission("suppliers:write")

    def test_read_only_cannot_write_anything(self) -> None:
        from app.auth.base import CurrentUser
        u = CurrentUser(
            user_id="u", org_id="o", clerk_org_id="c", role=ROLE_READ_ONLY
        )
        write_perms = [p for p in _SHOULD_HAVE if ":write" in p]
        for perm in write_perms:
            assert not u.has_permission(perm), (
                f"read_only CurrentUser must not have '{perm}'"
            )

    def test_org_user_can_write_alerts(self) -> None:
        from app.auth.base import CurrentUser
        u = CurrentUser(
            user_id="u", org_id="o", clerk_org_id="c", role=ROLE_ORG_USER
        )
        assert u.has_permission("alerts:write")

    def test_org_user_cannot_use_ai(self) -> None:
        from app.auth.base import CurrentUser
        u = CurrentUser(
            user_id="u", org_id="o", clerk_org_id="c", role=ROLE_ORG_USER
        )
        assert not u.has_permission("ai:use")
