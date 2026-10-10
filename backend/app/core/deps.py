"""
app/core/deps.py — FastAPI dependency functions.

These are the ONLY entry points through which route handlers obtain:
  - a database session    (get_db already in app.db.session)
  - the current user      (get_current_user)
  - permission guards     (require_permission factory)

Usage in a route:

    from app.core.deps import get_current_user, require_permission
    from app.auth.base import CurrentUser

    @router.get("/suppliers")
    async def list_suppliers(
        current_user: CurrentUser = Depends(require_permission("suppliers:read")),
        db: AsyncSession = Depends(get_db),
    ):
        ...
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Annotated

import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import (
    AuthenticationError,
    AuthorizationError,
    CurrentUser,
)
from app.auth.providers.jwt import JwtVerifier
from app.db.session import get_db

logger = structlog.get_logger(__name__)

# ── HTTP Bearer extractor ─────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_verifier() -> JwtVerifier:
    """Singleton JwtVerifier — constructed once, enforces cryptographically signed JWTs."""
    return JwtVerifier()


# ── Primary auth dependency ───────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Resolve the current authenticated user from the Bearer JWT.

    Raises AuthenticationError (→ 401) if the token is absent or invalid.
    Raises AuthorizationError (→ 403) if the token is valid but the principal
    has no active org membership.
    """
    if credentials is None:
        raise AuthenticationError("Authorization header is missing or not a Bearer token")

    verifier = _get_verifier()
    user = await verifier.verify(credentials.credentials, db_session=db)

    # Bind user context to structlog so every log line in this request carries it
    import structlog.contextvars as sv
    sv.bind_contextvars(
        user_id=user.user_id,
        org_id=user.org_id,
        role=user.role,
    )

    return user


# ── Permission guard factory ──────────────────────────────────────────────────

def require_permission(permission: str):
    """
    Return a FastAPI dependency that yields CurrentUser if the caller has
    *permission*, otherwise raises AuthorizationError.

    Example:
        @router.post("/suppliers")
        async def create_supplier(
            current_user: CurrentUser = Depends(require_permission("suppliers:write")),
        ):
            ...
    """
    async def _guard(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.has_permission(permission):
            raise AuthorizationError(
                f"This action requires the '{permission}' permission. "
                f"Your role '{current_user.role}' does not grant it."
            )
        return current_user

    # Give the inner function a unique name so FastAPI's dependency cache
    # doesn't accidentally de-duplicate guards for different permissions.
    _guard.__name__ = f"require_{permission.replace(':', '_')}"
    return _guard


# ── Typed shorthand aliases ────────────────────────────────────────────────────
# Use these in route signatures for cleaner type annotations.

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
