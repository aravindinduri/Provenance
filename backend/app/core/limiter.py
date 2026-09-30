"""
app/core/limiter.py — SlowAPI rate limiter setup.

Per arch §N.1:
  Rate limits: 1000 req/h per user, 10k/h per org; /ai/* 60/h per user; 429 with Retry-After.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    """
    Key function for rate limiting.
    Uses user_id or org_id if available on request.state (bound by auth),
    otherwise falls back to remote client IP.
    """
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"
    if hasattr(request.state, "org_id") and request.state.org_id:
        return f"org:{request.state.org_id}"
    return get_remote_address(request)


# Singleton Limiter instance. In production can use Redis storage; in-memory by default.
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["1000/hour"],
    headers_enabled=True,
)
