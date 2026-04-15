"""Strava OAuth2 helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

logger = structlog.get_logger(__name__)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


def get_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str | None = None,
) -> str:
    """Build Strava OAuth authorization URL."""
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "read,activity:read_all,profile:read_all",
    }
    if state:
        params["state"] = state
    return f"{STRAVA_AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """Exchange an authorization code for tokens.

    Returns:
        Dict with access_token, refresh_token, expires_at, athlete info.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

    logger.info(
        "strava_oauth.code_exchanged",
        athlete_id=data.get("athlete", {}).get("id"),
    )
    return data
