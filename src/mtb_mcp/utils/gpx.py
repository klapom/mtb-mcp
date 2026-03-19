"""GPX file parsing and writing utilities."""

from __future__ import annotations

import gpxpy
import gpxpy.gpx

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.utils.geo import haversine


def parse_gpx(gpx_data: str | bytes) -> list[GeoPoint]:
    """Parse GPX data into a list of GeoPoints with elevation.

    Handles both track points and route points. Track points take priority;
    if no tracks exist, falls back to route points; if neither, uses waypoints.

    Args:
        gpx_data: GPX XML as string or bytes.

    Returns:
        List of GeoPoint instances extracted from the GPX data.
    """
    if isinstance(gpx_data, bytes):
        gpx_data = gpx_data.decode("utf-8")

    gpx = gpxpy.parse(gpx_data)
    points: list[GeoPoint] = []

    # Prefer track points
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                points.append(
                    GeoPoint(
                        lat=float(pt.latitude),
                        lon=float(pt.longitude),
                        ele=float(pt.elevation) if pt.elevation is not None else None,
                    )
                )

    if points:
        return points

    # Fall back to route points
    for route in gpx.routes:
        for rpt in route.points:
            points.append(
                GeoPoint(
                    lat=float(rpt.latitude),
                    lon=float(rpt.longitude),
                    ele=float(rpt.elevation) if rpt.elevation is not None else None,
                )
            )

    if points:
        return points

    # Fall back to waypoints
    for wpt in gpx.waypoints:
        points.append(
            GeoPoint(
                lat=float(wpt.latitude),
                lon=float(wpt.longitude),
                ele=float(wpt.elevation) if wpt.elevation is not None else None,
            )
        )

    return points


def write_gpx(points: list[GeoPoint], name: str = "MTB Route") -> str:
    """Write GeoPoints to GPX XML string.

    Creates a single track with a single segment containing all points.

    Args:
        points: List of GeoPoint instances.
        name: Name for the GPX track.

    Returns:
        GPX XML as a string.
    """
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name=name)
    gpx.tracks.append(track)

    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for pt in points:
        segment.points.append(
            gpxpy.gpx.GPXTrackPoint(
                latitude=pt.lat,
                longitude=pt.lon,
                elevation=pt.ele,
            )
        )

    return gpx.to_xml()


def gpx_distance_km(points: list[GeoPoint]) -> float:
    """Calculate total distance of a GPX track in km.

    Sums haversine distances between consecutive points.

    Args:
        points: List of GeoPoint instances.

    Returns:
        Total distance in kilometers.
    """
    if len(points) < 2:
        return 0.0

    total = 0.0
    for i in range(1, len(points)):
        total += haversine(
            points[i - 1].lat,
            points[i - 1].lon,
            points[i].lat,
            points[i].lon,
        )
    return total


def gpx_elevation_gain(points: list[GeoPoint]) -> float:
    """Calculate total elevation gain in meters (only uphill segments).

    Ignores points without elevation data.

    Args:
        points: List of GeoPoint instances.

    Returns:
        Total elevation gain in meters.
    """
    gain = 0.0
    prev_ele: float | None = None

    for pt in points:
        if pt.ele is not None:
            if prev_ele is not None and pt.ele > prev_ele:
                gain += pt.ele - prev_ele
            prev_ele = pt.ele

    return gain
