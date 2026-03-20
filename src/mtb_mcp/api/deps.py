"""FastAPI dependency injection — client factories and shared state."""

from __future__ import annotations

from functools import lru_cache

from mtb_mcp.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    """Return a cached Settings singleton for the API lifetime."""
    return get_settings()


def resolve_location(
    lat: float | None,
    lon: float | None,
    settings: Settings | None = None,
) -> tuple[float, float]:
    """Resolve lat/lon, falling back to home location from settings."""
    if lat is not None and lon is not None:
        return lat, lon
    s = settings or get_cached_settings()
    return s.home_lat, s.home_lon
