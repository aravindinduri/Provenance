"""
app/auth/providers/clerk.py — Clerk JWT verifier.

Implements the TokenVerifier protocol from app.auth.base.
Everything Clerk-specific is isolated here.  The rest of the application
imports only CurrentUser and TokenVerifier from app.auth.base.

Verification steps:
  1. Fetch Clerk's JWKS (cached in Redis with a 1-hour TTL; falls back
     to an in-process cache if Redis is unavailable).
  2. Decode and verify the JWT (signature, iss, aud, exp).
  3. Extract claims: sub, org_id (Clerk org), org_role.
  4. Look up the matching internal Organization row to get the tenant UUID
     and the member's role/persona stored in organization_members.
  5. Return a CurrentUser.

Exit path: to swap Clerk for Keycloak (or any OIDC provider), implement a
new class here that satisfies the TokenVerifier protocol and update the
provider binding in app/core/deps.py.  No other file changes.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import structlog
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import (
    ROLE_PLATFORM_ADMIN,
    AuthenticationError,
    AuthorizationError,
    CurrentUser,
)
from app.config import get_settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# In-process JWKS cache (fallback when Redis unavailable)
# ---------------------------------------------------------------------------
_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600  # 1 hour


async def _fetch_jwks() -> dict[str, Any]:
    """Return the cached JWKS, refreshing if stale."""
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    settings = get_settings()
    url = settings.clerk_jwks_url
    if not url:
        raise AuthenticationError("CLERK_JWKS_URL is not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except httpx.HTTPError as exc:
        logger.warning("clerk_jwks_fetch_failed", error=str(exc))
        if _jwks_cache:
            # Serve stale rather than break all requests
            return _jwks_cache
        raise AuthenticationError("Unable to fetch JWKS from Clerk") from exc

    _jwks_cache = data
    _jwks_fetched_at = now
    return data


# ---------------------------------------------------------------------------
# ClerkVerifier
# ---------------------------------------------------------------------------

class ClerkVerifier:
    """
    Verifies Clerk-issued JWTs and resolves the caller to a CurrentUser.

    Constructed once at startup and injected via FastAPI's dependency system.
    The *db_session* is provided per-request by the caller (the FastAPI dep).
    """

    async def verify(self, token: str, db_session: AsyncSession) -> CurrentUser:  # type: ignore[override]
        """
        Verify *token* and return a populated CurrentUser.

        Unlike the base protocol, this implementation takes an extra
        *db_session* arg because we need to query organization_members.
        The FastAPI dependency in app/core/deps.py bridges this.
        """
        settings = get_settings()

        # ── 1. Decode JWT ────────────────────────────────────────────────────
        try:
            jwks = await _fetch_jwks()
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                issuer=settings.auth_issuer or None,
                audience=settings.auth_audience or None,
                options={
                    # audience check is optional when auth_audience is blank
                    "verify_aud": bool(settings.auth_audience),
                },
            )
        except ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired") from exc
        except JWTError as exc:
            raise AuthenticationError(f"Invalid token: {exc}") from exc

        # ── 2. Extract standard claims ────────────────────────────────────────
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token missing 'sub' claim")

        email: str | None = payload.get("email")

        # Clerk puts org context in these claims when a session is org-scoped
        clerk_org_id: str | None = payload.get("org_id")
        clerk_org_role: str | None = payload.get("org_role")  # e.g. "org:admin"

        # ── 3. Platform-admin shortcut ────────────────────────────────────────
        # A platform_admin token carries a custom claim set in the Clerk dashboard
        # session template: { "platform_admin": true }
        if payload.get("platform_admin") is True:
            return CurrentUser(
                user_id=user_id,
                org_id=None,
                clerk_org_id=clerk_org_id,
                role=ROLE_PLATFORM_ADMIN,
                email=email,
            )

        # ── 4. Resolve internal org + member record ────────────────────────────
        if not clerk_org_id:
            raise AuthorizationError(
                "Token is not scoped to an organization. "
                "Please select an organization in your Clerk session."
            )

        # Look up the internal org UUID from the Clerk org ID
        org_row = await db_session.execute(
            text(
                "SELECT id FROM organizations "
                "WHERE clerk_org_id = :coid AND deleted_at IS NULL"
            ),
            {"coid": clerk_org_id},
        )
        org_record = org_row.fetchone()
        if org_record is None:
            raise AuthorizationError(
                f"Organization '{clerk_org_id}' is not registered in Provenance. "
                "Complete organization setup before accessing the API."
            )

        internal_org_id: str = str(org_record[0])

        # Look up the member's role and persona
        member_row = await db_session.execute(
            text(
                "SELECT role, persona, assigned_categories "
                "FROM organization_members "
                "WHERE org_id = :oid AND user_id = :uid AND deleted_at IS NULL"
            ),
            {"oid": internal_org_id, "uid": user_id},
        )
        member_record = member_row.fetchone()

        if member_record is None:
            # Member not yet synced (race between webhook and first request).
            # Fall back to mapping Clerk's org role to our role enum.
            role = _map_clerk_role(clerk_org_role)
            persona = None
            assigned_categories: list[str] = []
            logger.warning(
                "clerk_member_not_synced",
                user_id=user_id,
                org_id=internal_org_id,
                clerk_role=clerk_org_role,
            )
        else:
            role, persona, assigned_categories = (
                member_record[0],
                member_record[1],
                list(member_record[2] or []),
            )

        return CurrentUser(
            user_id=user_id,
            org_id=internal_org_id,
            clerk_org_id=clerk_org_id,
            role=role,
            persona=persona,
            email=email,
            assigned_categories=assigned_categories,
        )


# ---------------------------------------------------------------------------
# Clerk role → internal role mapping
# ---------------------------------------------------------------------------

def _map_clerk_role(clerk_role: str | None) -> str:
    """
    Map Clerk's built-in org roles to our internal role strings.

    Clerk built-ins: org:admin, org:member, org:viewer
    Custom roles set in the Clerk dashboard should match our role names exactly
    (e.g. "analyst", "org_user", "read_only") — those pass through unchanged.
    """
    _MAPPING = {
        "org:admin": "org_admin",
        "org:member": "analyst",
        "org:viewer": "read_only",
    }
    if clerk_role is None:
        return "org_user"
    return _MAPPING.get(clerk_role, clerk_role)


# ---------------------------------------------------------------------------
# Webhook payload helpers (used by the webhook handler, not the verifier)
# ---------------------------------------------------------------------------

def verify_clerk_webhook(payload: bytes, svix_id: str, svix_timestamp: str, svix_signature: str) -> dict[str, Any]:
    """
    Verify a Clerk webhook payload using the Svix signing secret.

    Returns the parsed JSON body on success.
    Raises AuthenticationError on failure.

    Clerk uses the Svix webhook library for delivery.  The verification
    algorithm is HMAC-SHA256 over `"{svix_id}.{svix_timestamp}.{body}"`.
    """
    import base64
    import hashlib
    import hmac

    settings = get_settings()
    secret = settings.clerk_webhook_secret
    if not secret:
        raise AuthenticationError("CLERK_WEBHOOK_SECRET is not configured")

    # Svix secrets are base64-encoded with a "whsec_" prefix
    if secret.startswith("whsec_"):
        secret = secret[len("whsec_"):]
    try:
        key = base64.b64decode(secret)
    except Exception as exc:
        raise AuthenticationError("Malformed CLERK_WEBHOOK_SECRET") from exc

    signed_content = f"{svix_id}.{svix_timestamp}.{payload.decode()}".encode()
    expected = base64.b64encode(
        hmac.new(key, signed_content, hashlib.sha256).digest()
    ).decode()

    # svix_signature may be a comma-separated list of "v1,<sig>" entries
    for sig_entry in svix_signature.split(" "):
        if "," in sig_entry:
            _, sig = sig_entry.split(",", 1)
        else:
            sig = sig_entry
        if hmac.compare_digest(expected, sig):
            try:
                return json.loads(payload)  # type: ignore[no-any-return]
            except json.JSONDecodeError as exc:
                raise AuthenticationError("Webhook payload is not valid JSON") from exc

    raise AuthenticationError("Webhook signature verification failed")
