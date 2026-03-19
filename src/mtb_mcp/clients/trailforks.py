"""Trailforks client -- currently a placeholder as API access requires approval."""

from __future__ import annotations

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.trail import Trail


class TrailforksClient(BaseClient):
    """Client for Trailforks trail data.

    Note: Trailforks does not provide a public API.
    This is a placeholder for potential future integration
    if API access is granted.
    """

    def __init__(self) -> None:
        super().__init__(base_url="https://www.trailforks.com", rate_limit=0.5)

    async def search_trails(
        self, lat: float, lon: float, radius_km: float = 30.0,
    ) -> list[Trail]:
        """Search trails -- not yet implemented."""
        return []

    async def is_available(self) -> bool:
        """Trailforks API is not publicly available."""
        return False
