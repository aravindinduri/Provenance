"""
tests/unit/test_auth_base.py

Unit tests for app.auth.base:
  - CurrentUser construction and helpers
  - has_permission() function
  - AuthenticationError / AuthorizationError carry the right detail
  - TokenVerifier is a runtime-checkable Protocol
"""

from __future__ import annotations

import pytest

from app.auth.base import (
    PERMISSIONS,
    ROLE_ANALYST,
    ROLE_ORG_ADMIN,
    ROLE_ORG_USER,
    ROLE_PLATFORM_ADMIN,
    ROLE_READ_ONLY,
    AuthenticationError,
    AuthorizationError,
    CurrentUser,
    TokenVerifier,
    has_permission,
)


# ---------------------------------------------------------------------------
# CurrentUser
# ---------------------------------------------------------------------------

class TestCurrentUser:
    def test_basic_construction(self) -> None:
        u = CurrentUser(
            user_id="user_abc",
            org_id="org-uuid",
            clerk_org_id="clerk_org_abc",
            role=ROLE_ANALYST,
            email="analyst@example.com",
        )
        assert u.user_id == "user_abc"
        assert u.role == ROLE_ANALYST
        assert u.persona is None
        assert u.assigned_categories == []

    def test_frozen(self) -> None:
        u = CurrentUser(
            user_id="u1",
            org_id="o1",
            clerk_org_id="c1",
            role=ROLE_ORG_USER,
        )
        with pytest.raises(AttributeError):
            u.role = ROLE_ORG_ADMIN  # type: ignore[misc]

    def test_is_platform_admin_true(self) -> None:
        u = CurrentUser(
            user_id="admin",
            org_id=None,
            clerk_org_id=None,
            role=ROLE_PLATFORM_ADMIN,
        )
        assert u.is_platform_admin is True

    def test_is_platform_admin_false(self) -> None:
        u = CurrentUser(
            user_id="u",
            org_id="o",
            clerk_org_id="c",
            role=ROLE_ORG_ADMIN,
        )
        assert u.is_platform_admin is False

    def test_has_permission_delegates_to_module_fn(self) -> None:
        u = CurrentUser(
            user_id="u",
            org_id="o",
            clerk_org_id="c",
            role=ROLE_ANALYST,
        )
        assert u.has_permission("suppliers:write") is True
        assert u.has_permission("admin:write") is False

    def test_assigned_categories_default_is_empty_list(self) -> None:
        u = CurrentUser(
            user_id="u",
            org_id="o",
            clerk_org_id="c",
            role=ROLE_ORG_USER,
        )
        # Must be a new list, not a shared default
        assert u.assigned_categories == []
        assert u.assigned_categories is not CurrentUser(
            user_id="u2", org_id="o", clerk_org_id="c", role=ROLE_ORG_USER
        ).assigned_categories


# ---------------------------------------------------------------------------
# has_permission
# ---------------------------------------------------------------------------

class TestHasPermission:
    def test_unknown_role_returns_false(self) -> None:
        assert has_permission("made_up_role", "org:read") is False

    def test_empty_permission_returns_false(self) -> None:
        assert has_permission(ROLE_ORG_ADMIN, "nonexistent:perm") is False

    def test_platform_admin_has_all_permissions(self) -> None:
        all_perms = set().union(*PERMISSIONS.values())
        for perm in all_perms:
            assert has_permission(ROLE_PLATFORM_ADMIN, perm), \
                f"platform_admin should have '{perm}'"

    def test_read_only_has_no_write_permissions(self) -> None:
        write_perms = {p for p in PERMISSIONS[ROLE_PLATFORM_ADMIN] if ":write" in p}
        for perm in write_perms:
            assert not has_permission(ROLE_READ_ONLY, perm), \
                f"read_only must NOT have '{perm}'"

    def test_read_only_has_read_permissions(self) -> None:
        for perm in PERMISSIONS[ROLE_READ_ONLY]:
            assert has_permission(ROLE_READ_ONLY, perm)


# ---------------------------------------------------------------------------
# Auth exceptions
# ---------------------------------------------------------------------------

class TestAuthExceptions:
    def test_authentication_error_default_message(self) -> None:
        exc = AuthenticationError()
        assert exc.detail == "Authentication required"
        assert str(exc) == "Authentication required"

    def test_authentication_error_custom_message(self) -> None:
        exc = AuthenticationError("Token has expired")
        assert exc.detail == "Token has expired"

    def test_authorization_error_default_message(self) -> None:
        exc = AuthorizationError()
        assert exc.detail == "Insufficient permissions"

    def test_authorization_error_custom_message(self) -> None:
        exc = AuthorizationError("Requires org_admin role")
        assert exc.detail == "Requires org_admin role"

    def test_authentication_error_is_exception(self) -> None:
        with pytest.raises(AuthenticationError, match="expired"):
            raise AuthenticationError("expired")

    def test_authorization_error_is_exception(self) -> None:
        with pytest.raises(AuthorizationError):
            raise AuthorizationError()


# ---------------------------------------------------------------------------
# TokenVerifier Protocol
# ---------------------------------------------------------------------------

class TestTokenVerifierProtocol:
    def test_class_not_implementing_verify_fails_isinstance(self) -> None:
        class NotAVerifier:
            pass

        assert not isinstance(NotAVerifier(), TokenVerifier)

    def test_class_implementing_verify_passes_isinstance(self) -> None:
        class FakeVerifier:
            async def verify(self, token: str) -> CurrentUser:
                return CurrentUser(
                    user_id="u",
                    org_id="o",
                    clerk_org_id="c",
                    role=ROLE_ORG_USER,
                )

        assert isinstance(FakeVerifier(), TokenVerifier)
