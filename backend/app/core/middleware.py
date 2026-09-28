"""
app/core/middleware.py — Request-level middleware.

RequestIdMiddleware
  Stamps every request with a UUID in `request.state.request_id` and echoes
  it as `X-Request-Id` on every response.  Correlates API calls to logs and
  Sentry traces.

TenantContextMiddleware
  Sets the `app.current_org_id` PostgreSQL session parameter that the RLS
  policies read.  This is the third layer of tenant isolation (after the
  route-level permission guard and the repository-level org_id filter).

  IMPORTANT: This middleware only sets the session variable. It does NOT
  authenticate the request — that is done by the FastAPI dependency
  get_current_user(). The middleware runs before dependencies, so it reads
  org_id from request.state (populated by the auth dependency during the
  request lifecycle via structlog context vars). For the RLS approach we use
  here, the middleware wraps the DB session setter in a per-request hook
  rather than doing it in the middleware itself (since middleware runs before
  FastAPI resolves dependencies).

  The actual SET is done in the get_db() dependency override defined below.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique request ID to every incoming request and outgoing response.

    The ID is taken from the `X-Request-Id` header if present (e.g. from an
    upstream load balancer), otherwise generated.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        import structlog.contextvars as sv
        sv.clear_contextvars()
        sv.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


# ---------------------------------------------------------------------------
# RLS session-variable setter
# ---------------------------------------------------------------------------
# We set app.current_org_id as a PostgreSQL session variable inside the DB
# session lifecycle rather than as an ASGI middleware, because the org_id is
# only known after JWT verification (which is a FastAPI dependency, not a
# middleware).
#
# The pattern: override get_db() in app/db/session.py with a version that
# sets the session variable at transaction start. We expose the helper here
# so it can be tested independently.

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Any


async def set_rls_org(session: AsyncSession, org_id: str | None) -> None:
    """
    Set `app.current_org_id` in the current PostgreSQL session.

    Called at the start of every request that has an authenticated tenant.
    When org_id is None (e.g. platform_admin cross-tenant ops) we set it to
    an empty string so policies that use `current_setting('app.current_org_id',
    true)` don't error.
    """
    value = str(org_id) if org_id else ""
    await session.execute(
        text("SELECT set_config('app.current_org_id', :val, true)"),
        {"val": value},
    )


async def get_tenant_db(
    request: Request,
    db: AsyncSession,
) -> AsyncSession:
    """
    A thin wrapper around get_db that also sets the RLS session variable.

    Route handlers that need RLS enforcement should depend on this instead of
    get_db directly. The auth dependency must run first (ensured by FastAPI's
    dependency resolution order when both are declared).

    Usage:
        from app.core.middleware import get_tenant_db
        from app.core.deps import get_current_user

        @router.get("/suppliers")
        async def list_suppliers(
            current_user: CurrentUser = Depends(get_current_user),
            db: AsyncSession = Depends(get_tenant_db),
        ):
            ...

    Note: since get_current_user also Depends(get_db), FastAPI's dependency
    cache ensures a single session is used per request — the same session
    that had its RLS variable set.
    """
    org_id: str | None = None
    if hasattr(request.state, "current_user"):
        org_id = request.state.current_user.org_id
    await set_rls_org(db, org_id)
    return db
