"""
app/auth/base.py — TokenVerifier protocol and CurrentUser value-object.

Application code ONLY imports from this module.
Clerk-specific code lives in providers/clerk.py and is never referenced
outside the auth package — swapping providers is one new file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Value object: what every request handler sees after auth
# ---------------------------------------------------------------------------

# Role constants — single source of truth for permission checks
ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_ORG_ADMIN = "org_admin"
ROLE_ANALYST = "analyst"
ROLE_ORG_USER = "org_user"
ROLE_READ_ONLY = "read_only"

# Permission strings consumed by require_permission()
PERMISSIONS: dict[str, set[str]] = {
    ROLE_PLATFORM_ADMIN: {
        # inherits everything
        "platform:read",
        "platform:write",
        "org:read",
        "org:write",
        "members:read",
        "members:write",
        "suppliers:read",
        "suppliers:write",
        "alerts:read",
        "alerts:write",
        "documents:read",
        "documents:write",
        "graph:read",
        "graph:write",
        "ai:use",
        "admin:read",
        "admin:write",
    },
    ROLE_ORG_ADMIN: {
        "org:read",
        "org:write",
        "members:read",
        "members:write",
        "suppliers:read",
        "suppliers:write",
        "alerts:read",
        "alerts:write",
        "documents:read",
        "documents:write",
        "graph:read",
        "graph:write",
        "ai:use",
    },
    ROLE_ANALYST: {
        "org:read",
        "members:read",
        "suppliers:read",
        "suppliers:write",
        "alerts:read",
        "alerts:write",
        "documents:read",
        "documents:write",
        "graph:read",
        "graph:write",
        "ai:use",
    },
    ROLE_ORG_USER: {
        "org:read",
        "members:read",
        "suppliers:read",
        "alerts:read",
        "alerts:write",   # can acknowledge/dismiss own alerts
        "documents:read",
        "graph:read",
    },
    ROLE_READ_ONLY: {
        "org:read",
        "members:read",
        "suppliers:read",
        "alerts:read",
        "documents:read",
        "graph:read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Return True if *role* grants *permission*."""
    return permission in PERMISSIONS.get(role, set())


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """
    The authenticated principal, resolved from a verified JWT.

    Injected into every request handler via FastAPI's dependency system.
    Never constructed from request body data — only from the verified token.

    Attributes:
        user_id   Clerk ``sub`` claim (stable, unique user identifier).
        org_id    The tenant UUID from the internal organizations table.
                  None only for platform_admin calls that operate cross-tenant.
        clerk_org_id  Clerk's own org identifier (used for webhook sync).
        role      RBAC role string; one of the ROLE_* constants above.
        persona   UX hint (risk_manager / category_manager / other), NOT a
                  permission boundary — see arch §12.2.
        email     From the verified token claims, for logging / notifications.
        assigned_categories  Category-manager scoping list (empty = all).
    """

    user_id: str
    org_id: str | None
    clerk_org_id: str | None
    role: str
    persona: str | None = None
    email: str | None = None
    assigned_categories: list[str] = field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        return has_permission(self.role, permission)

    @property
    def is_platform_admin(self) -> bool:
        return self.role == ROLE_PLATFORM_ADMIN


# ---------------------------------------------------------------------------
# Protocol — the only contract application code depends on
# ---------------------------------------------------------------------------

@runtime_checkable
class TokenVerifier(Protocol):
    """
    Verify a raw Bearer token and return the authenticated principal.

    Implementations live in providers/.  The application layer calls this
    via the FastAPI dependency and never touches the implementation directly.
    """

    async def verify(self, token: str) -> CurrentUser:
        """
        Verify *token* and return a populated CurrentUser.

        Raises:
            AuthenticationError  if the token is missing, malformed, expired,
                                 or fails signature verification.
            AuthorizationError   if the token is valid but the principal has
                                 no active membership in any org (and is not
                                 a platform_admin).
        """
        ...


# ---------------------------------------------------------------------------
# Typed auth exceptions
# ---------------------------------------------------------------------------

class AuthenticationError(Exception):
    """JWT is missing, malformed, expired, or fails signature verification."""

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(detail)
        self.detail = detail


class AuthorizationError(Exception):
    """Principal is authenticated but lacks the required permission."""

    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(detail)
        self.detail = detail
