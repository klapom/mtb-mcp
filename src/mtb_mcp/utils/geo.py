"""Geographic utility functions."""

from __future__ import annotations

import math

# Earth mean radius in km (WGS-84)
_EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km between two WGS84 points.

    Uses the Haversine formula.
    """
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return _EARTH_RADIUS_KM * c


def bbox_from_center(
    lat: float, lon: float, radius_km: float
) -> tuple[float, float, float, float]:
    """Create bounding box (south, west, north, east) from center point + radius.

    Uses a simple approximation that works well for small to moderate radii.

    Returns:
        Tuple of (south, west, north, east) in degrees.
    """
    delta_lat = math.degrees(radius_km / _EARTH_RADIUS_KM)
    # Longitude degrees shrink with cos(latitude)
    delta_lon = math.degrees(radius_km / (_EARTH_RADIUS_KM * math.cos(math.radians(lat))))

    south = lat - delta_lat
    north = lat + delta_lat
    west = lon - delta_lon
    east = lon + delta_lon

    return (south, west, north, east)


def validate_coordinates(lat: float, lon: float) -> bool:
    """Check if coordinates are valid WGS84.

    lat must be in [-90, 90], lon must be in [-180, 180].
    """
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Calculate geographic midpoint of two WGS84 coordinates.

    Uses the spherical midpoint formula for accuracy on a globe.

    Returns:
        Tuple of (lat, lon) in degrees.
    """
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlon = lon2_r - lon1_r

    bx = math.cos(lat2_r) * math.cos(dlon)
    by = math.cos(lat2_r) * math.sin(dlon)

    mid_lat = math.atan2(
        math.sin(lat1_r) + math.sin(lat2_r),
        math.sqrt((math.cos(lat1_r) + bx) ** 2 + by**2),
    )
    mid_lon = lon1_r + math.atan2(by, math.cos(lat1_r) + bx)

    return (math.degrees(mid_lat), math.degrees(mid_lon))
