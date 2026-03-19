"""Wahoo Fitness API client -- placeholder for future OAuth2 integration."""

from __future__ import annotations

from mtb_mcp.clients.base import BaseClient


class WahooClient(BaseClient):
    """Client for Wahoo Fitness API.

    Future: OAuth2 integration for workout sync.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        super().__init__(base_url="https://api.wahooligan.com", rate_limit=2.0)
        self._client_id = client_id
        self._client_secret = client_secret

    async def is_available(self) -> bool:
        """Wahoo API integration is not yet available."""
        return False
