"""JWT token creation and verification."""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid

import jwt

# Access token: 60 minutes
ACCESS_TOKEN_EXPIRE_SECONDS = 3600
# Refresh token: 30 days
REFRESH_TOKEN_EXPIRE_SECONDS = 30 * 24 * 3600


def create_access_token(user_id: str, secret: str) -> str:
    """Create a short-lived access token."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    token: str = jwt.encode(payload, secret, algorithm="HS256")
    return token


def create_refresh_token(user_id: str, secret: str) -> tuple[str, str]:
    """Create a long-lived refresh token.

    Returns:
        Tuple of (raw_token, token_hash) — store the hash, return the raw token.
    """
    raw = secrets.token_urlsafe(48)
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE_SECONDS,
        "jti": raw,
        "type": "refresh",
    }
    token: str = jwt.encode(payload, secret, algorithm="HS256")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def decode_token(token: str, secret: str) -> dict[str, object]:
    """Decode and verify a JWT token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is invalid.
    """
    payload: dict[str, object] = jwt.decode(token, secret, algorithms=["HS256"])
    return payload
