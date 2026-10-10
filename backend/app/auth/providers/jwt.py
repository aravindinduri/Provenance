"""
app/auth/providers/jwt.py — Authentic self-contained JWT token verifier.
Implements the TokenVerifier protocol from app.auth.base.
Zero dummy/mock tokens. Verifies cryptographically signed JWTs issued on login/register.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import (
    AuthenticationError,
    AuthorizationError,
    CurrentUser,
    ROLE_ORG_ADMIN,
    ROLE_ORG_USER,
)
from app.auth.security import decode_access_token
from app.config import get_settings

logger = structlog.get_logger(__name__)


class JwtVerifier:
    """
    Verifies cryptographically signed JWTs issued by the Provenance auth service.
    Resolves the verified claims to an authentic CurrentUser.
    """

    async def verify(self, token: str, db_session: AsyncSession) -> CurrentUser:
        settings = get_settings()

        # ── 1. Decode & Verify JWT ───────────────────────────────────────────
        try:
            payload = decode_access_token(token)
        except ExpiredSignatureError as exc:
            raise AuthenticationError("Authentication token has expired. Please log in again.") from exc
        except JWTError as exc:
            # Check if Clerk is configured as an alternative external provider
            if settings.clerk_jwks_url:
                from app.auth.providers.clerk import ClerkVerifier
                return await ClerkVerifier().verify(token, db_session)
            raise AuthenticationError(f"Invalid authentication token: {exc}") from exc

        # ── 2. Extract Claims ─────────────────────────────────────────────────
        user_id = payload.get("sub")
        email = payload.get("email", "")
        token_org_id = payload.get("org_id")
        assigned_categories = payload.get("assigned_categories", [])

        if not user_id:
            raise AuthenticationError("Token payload missing subject identifier ('sub')")

        # ── 3. Verify User in Database ────────────────────────────────────────
        user_row = await db_session.execute(
            text(
                "SELECT id, email, is_active FROM users "
                "WHERE (id::text = :sub OR email = :email) AND deleted_at IS NULL "
                "LIMIT 1"
            ),
            {"sub": str(user_id), "email": email},
        )
        user_record = user_row.fetchone()

        if not user_record:
            raise AuthenticationError("User does not exist or has been removed.")

        if not user_record[2]:
            raise AuthenticationError("User account has been deactivated.")

        user_id = str(user_record[0])
        email = str(user_record[1])

        # ── 4. Resolve Organization Membership from Database ─────────────────
        conditions = [
            "(om.user_id = :uid OR om.user_id = :email)",
            "om.deleted_at IS NULL",
            "o.deleted_at IS NULL",
        ]
        params: dict[str, Any] = {"uid": str(user_id), "email": email}
        if token_org_id:
            conditions.append("om.org_id = :req_org")
            params["req_org"] = uuid.UUID(str(token_org_id))

        query_sql = (
            "SELECT om.org_id, om.role, om.persona, o.clerk_org_id "
            "FROM organization_members om "
            "JOIN organizations o ON o.id = om.org_id "
            f"WHERE {' AND '.join(conditions)} "
            "ORDER BY om.created_at ASC LIMIT 1"
        )
        member_row = await db_session.execute(text(query_sql), params)
        member = member_row.fetchone()
        if not member:
            raise AuthorizationError("User is not an active member of any organization.")

        resolved_org_id = str(member[0])
        role = member[1] or payload.get("role", ROLE_ORG_USER)
        persona = member[2] or payload.get("persona", "risk_manager")
        clerk_org_id = member[3]

        return CurrentUser(
            user_id=str(user_id),
            org_id=resolved_org_id,
            clerk_org_id=clerk_org_id,
            role=role,
            persona=persona,
            email=email,
            assigned_categories=assigned_categories,
        )
