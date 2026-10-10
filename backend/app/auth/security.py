"""
app/auth/security.py — Cryptographic password hashing and JWT generation.
Zero dummy/mock dependencies. Uses standard PBKDF2-HMAC-SHA256 and python-jose.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.config import get_settings

DEFAULT_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a cryptographically secure random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        DEFAULT_ITERATIONS,
    )
    return f"pbkdf2_sha256${DEFAULT_ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hex = parts[3]

        computed = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        ).hex()

        return hmac.compare_digest(computed, expected_hex)
    except Exception:
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a signed JWT access token for an authenticated user."""
    settings = get_settings()
    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET environment variable is not configured. Please set JWT_SECRET in .env.")

    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.auth_issuer or settings.otel_service_name or "provenance-api",
    })

    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify signature and expiration of a JWT access token."""
    settings = get_settings()
    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET environment variable is not configured. Please set JWT_SECRET in .env.")

    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": True},
    )
