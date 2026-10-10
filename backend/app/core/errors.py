"""
app/core/errors.py — RFC 9457 problem+json error helpers.

All error responses from the API use this shape:
  {
    "type":     "https://api.provenance.app/errors/<slug>",
    "title":    "<human-readable title>",
    "status":   <HTTP status code>,
    "detail":   "<specific detail>",
    "instance": "<request path>",
    "request_id": "<X-Request-Id value>",
    "errors":   [ { "field": "…", "code": "…" } ]   # optional
  }
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

_BASE_URI = "https://api.provenance.app/errors"

MEDIA_TYPE = "application/problem+json"


def _problem(
    request: Request,
    *,
    type_slug: str,
    title: str,
    status_code: int,
    detail: str,
    errors: list[dict[str, str]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{_BASE_URI}/{type_slug}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
        "request_id": request.state.request_id
        if hasattr(request.state, "request_id")
        else None,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=MEDIA_TYPE,
        headers={"X-Request-Id": body.get("request_id") or ""},
    )


# ── Convenience constructors ──────────────────────────────────────────────────

def unauthorized(request: Request, detail: str = "Authentication required") -> JSONResponse:
    return _problem(
        request,
        type_slug="unauthorized",
        title="Unauthorized",
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def forbidden(request: Request, detail: str = "Insufficient permissions") -> JSONResponse:
    return _problem(
        request,
        type_slug="forbidden",
        title="Forbidden",
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def not_found(request: Request, detail: str = "Resource not found") -> JSONResponse:
    return _problem(
        request,
        type_slug="not-found",
        title="Not Found",
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def conflict(request: Request, detail: str = "Resource already exists") -> JSONResponse:
    return _problem(
        request,
        type_slug="conflict",
        title="Conflict",
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def bad_request(request: Request, detail: str = "Bad request") -> JSONResponse:
    return _problem(
        request,
        type_slug="bad-request",
        title="Bad Request",
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def rate_limit_exceeded(
    request: Request,
    detail: str = "Rate limit exceeded",
    retry_after: int = 60,
) -> JSONResponse:
    res = _problem(
        request,
        type_slug="rate-limit-exceeded",
        title="Rate Limit Exceeded",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
    )
    res.headers["Retry-After"] = str(retry_after)
    return res


def unprocessable(
    request: Request,
    detail: str = "Validation failed",
    errors: list[dict[str, str]] | None = None,
) -> JSONResponse:
    return _problem(
        request,
        type_slug="validation-error",
        title="Validation Failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
        errors=errors,
    )


def internal_error(request: Request, detail: str = "An unexpected error occurred") -> JSONResponse:
    return _problem(
        request,
        type_slug="internal-server-error",
        title="Internal Server Error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


# ── FastAPI exception handlers ────────────────────────────────────────────────
# Register these with app.add_exception_handler() in main.py

from slowapi.errors import RateLimitExceeded  # noqa: E402

from app.auth.base import AuthenticationError, AuthorizationError  # noqa: E402


async def authentication_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AuthenticationError)
    return unauthorized(request, detail=exc.detail)


async def authorization_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AuthorizationError)
    return forbidden(request, detail=exc.detail)


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)
    retry_after = 60
    return rate_limit_exceeded(
        request,
        detail=f"Rate limit exceeded: {exc.detail}",
        retry_after=retry_after,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI/Pydantic ValidationError with RFC 9457 shape."""
    from fastapi.exceptions import RequestValidationError

    assert isinstance(exc, RequestValidationError)
    field_errors = [
        {
            "field": ".".join(str(loc) for loc in e["loc"][1:]) or str(e["loc"]),
            "code": e["type"],
            "message": e["msg"],
        }
        for e in exc.errors()
    ]
    return unprocessable(
        request,
        detail="Request body or parameters failed validation",
        errors=field_errors,
    )


async def ai_provider_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle AIProviderError gracefully with RFC 9457 shape and clean diagnostics."""
    from app.modules.ai.provider import AIProviderError

    assert isinstance(exc, AIProviderError)
    status_code = exc.status_code if exc.status_code in (400, 401, 403, 404, 429, 502, 503) else status.HTTP_502_BAD_GATEWAY
    return _problem(
        request,
        type_slug="ai-provider-error",
        title="AI Service Error",
        status_code=status_code,
        detail=str(exc),
    )
