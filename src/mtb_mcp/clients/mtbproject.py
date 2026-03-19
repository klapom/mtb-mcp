"""MTB Project REST API client."""

from __future__ import annotations

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.trail import Trail


class MTBProjectClient(BaseClient):
    """Client for MTB Project (singletracks.com) trail data.

    Note: Limited availability outside North America.
    """

    def __init__(self) -> None:
        super().__init__(base_url="https://www.mtbproject.com/data", rate_limit=1.0)

    async def search_trails(
        self, lat: float, lon: float, radius_km: float = 30.0,
    ) -> list[Trail]:
        """Search for MTB trails. Limited to North America coverage."""
        return []

    async def is_available(self) -> bool:
        """MTB Project API is not yet integrated."""
        return False
