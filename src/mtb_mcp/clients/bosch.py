"""Bosch eBike Cloud API client -- placeholder for future integration."""

from __future__ import annotations

from mtb_mcp.clients.base import BaseClient


class BoschClient(BaseClient):
    """Client for Bosch eBike Cloud API.

    Future: Battery status, ride history, motor diagnostics.
    Requires Bosch Developer Program enrollment.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        super().__init__(base_url="https://api.bosch-ebike.com", rate_limit=2.0)
        self._client_id = client_id
        self._client_secret = client_secret

    async def get_battery_status(self) -> dict[str, object] | None:
        """Get current battery status -- not yet available."""
        return None

    async def is_available(self) -> bool:
        """Bosch eBike Cloud API is not yet available."""
        return False
