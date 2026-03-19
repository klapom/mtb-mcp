"""Match GPS traces to known OSM trails."""

from __future__ import annotations

from dataclasses import dataclass

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.trail import Trail
from mtb_mcp.utils.geo import haversine


@dataclass
class TrailMatch:
    """Result of matching a GPS trace to a known trail."""

    trail: Trail
    overlap_pct: float  # 0-100
    distance_avg_m: float  # average distance of GPS points to trail


def _point_to_segment_distance_m(
    point: GeoPoint,
    seg_start: GeoPoint,
    seg_end: GeoPoint,
) -> float:
    """Calculate approximate distance from a point to a line segment in meters.

    Uses projection onto the segment. If the projection falls outside
    the segment, returns distance to the nearest endpoint.
    """
    # Use flat-earth approximation for small distances (adequate for buffer checks)
    d_start = haversine(point.lat, point.lon, seg_start.lat, seg_start.lon) * 1000.0
    d_end = haversine(point.lat, point.lon, seg_end.lat, seg_end.lon) * 1000.0
    seg_len = haversine(seg_start.lat, seg_start.lon, seg_end.lat, seg_end.lon) * 1000.0

    if seg_len < 0.01:
        # Degenerate segment
        return d_start

    # Project point onto segment using distances (law of cosines approach)
    # t = projection parameter along segment [0,1]
    # Using the formula: cos(A) = (a^2 + c^2 - b^2) / (2*a*c)
    # where a=seg_len, b=d_end, c=d_start
    cos_a_num = seg_len**2 + d_start**2 - d_end**2
    cos_a_den = 2.0 * seg_len * d_start

    if cos_a_den < 0.01:
        return d_start

    cos_a = cos_a_num / cos_a_den
    cos_a = max(-1.0, min(1.0, cos_a))

    # Projection distance along segment
    proj = d_start * cos_a

    if proj < 0:
        return d_start
    if proj > seg_len:
        return d_end

    # Perpendicular distance using Pythagorean theorem
    perp_sq = d_start**2 - proj**2
    if perp_sq < 0:
        return min(d_start, d_end)

    return float(perp_sq**0.5)


def _min_distance_to_trail_m(point: GeoPoint, trail: Trail) -> float:
    """Calculate minimum distance from a GPS point to any segment of a trail."""
    if not trail.geometry:
        return float("inf")

    if len(trail.geometry) == 1:
        return haversine(
            point.lat, point.lon,
            trail.geometry[0].lat, trail.geometry[0].lon,
        ) * 1000.0

    min_dist = float("inf")
    for i in range(len(trail.geometry) - 1):
        dist = _point_to_segment_distance_m(
            point, trail.geometry[i], trail.geometry[i + 1]
        )
        if dist < min_dist:
            min_dist = dist

    return min_dist


def match_trails(
    gps_points: list[GeoPoint],
    known_trails: list[Trail],
    buffer_m: float = 25.0,
) -> list[TrailMatch]:
    """Match GPS trace to known OSM trails.

    Algorithm:
    1. For each known trail, check how many GPS points are within buffer_m
    2. Calculate overlap percentage (matching points / total GPS points considered)
    3. Score by overlap percentage
    4. Return matches sorted by overlap, filtered > 30%
    """
    if not gps_points or not known_trails:
        return []

    results: list[TrailMatch] = []

    for trail in known_trails:
        if not trail.geometry:
            continue

        matching_count = 0
        total_distance = 0.0

        for point in gps_points:
            dist = _min_distance_to_trail_m(point, trail)
            if dist <= buffer_m:
                matching_count += 1
                total_distance += dist

        if matching_count == 0:
            continue

        overlap_pct = (matching_count / len(gps_points)) * 100.0
        avg_dist = total_distance / matching_count

        if overlap_pct > 30.0:
            results.append(TrailMatch(
                trail=trail,
                overlap_pct=round(overlap_pct, 1),
                distance_avg_m=round(avg_dist, 1),
            ))

    results.sort(key=lambda m: m.overlap_pct, reverse=True)
    return results


@dataclass
class RideSegment:
    """A tagged segment of a GPS ride."""

    start_index: int
    end_index: int
    trail_name: str
    trail_difficulty: str | None
    overlap_confidence: float  # 0-100

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary representation."""
        return {
            "start_index": self.start_index,
            "end_index": self.end_index,
            "trail_name": self.trail_name,
            "trail_difficulty": self.trail_difficulty,
            "overlap_confidence": self.overlap_confidence,
        }


def tag_ride_segments(
    gps_points: list[GeoPoint],
    trails: list[Trail],
    buffer_m: float = 25.0,
    min_consecutive: int = 3,
) -> list[dict[str, object]]:
    """Tag sections of a GPS trace with trail names.

    Returns list of segments with:
    - start_index, end_index (indices into gps_points)
    - trail_name
    - trail_difficulty
    - overlap_confidence
    """
    if not gps_points or not trails:
        return []

    # For each GPS point, find the closest trail within buffer
    point_trails: list[Trail | None] = []
    point_distances: list[float] = []

    for point in gps_points:
        best_trail: Trail | None = None
        best_dist = float("inf")

        for trail in trails:
            if not trail.geometry:
                continue
            dist = _min_distance_to_trail_m(point, trail)
            if dist <= buffer_m and dist < best_dist:
                best_trail = trail
                best_dist = dist

        point_trails.append(best_trail)
        point_distances.append(best_dist if best_trail is not None else float("inf"))

    # Group consecutive points on the same trail into segments
    segments: list[RideSegment] = []
    current_trail: Trail | None = None
    seg_start = 0
    seg_distances: list[float] = []

    for i, pt_trail in enumerate(point_trails):
        trail_id = pt_trail.osm_id if pt_trail is not None else None
        current_id = current_trail.osm_id if current_trail is not None else None

        if trail_id != current_id:
            # Flush previous segment
            if current_trail is not None and (i - seg_start) >= min_consecutive:
                confidence = _segment_confidence(seg_distances, buffer_m)
                segments.append(RideSegment(
                    start_index=seg_start,
                    end_index=i - 1,
                    trail_name=current_trail.name or f"OSM #{current_trail.osm_id}",
                    trail_difficulty=(
                        current_trail.mtb_scale.value if current_trail.mtb_scale else None
                    ),
                    overlap_confidence=round(confidence, 1),
                ))

            current_trail = pt_trail
            seg_start = i
            seg_distances = []

        if pt_trail is not None:
            seg_distances.append(point_distances[i])

    # Flush last segment
    if current_trail is not None and (len(point_trails) - seg_start) >= min_consecutive:
        confidence = _segment_confidence(seg_distances, buffer_m)
        segments.append(RideSegment(
            start_index=seg_start,
            end_index=len(point_trails) - 1,
            trail_name=current_trail.name or f"OSM #{current_trail.osm_id}",
            trail_difficulty=(
                current_trail.mtb_scale.value if current_trail.mtb_scale else None
            ),
            overlap_confidence=round(confidence, 1),
        ))

    return [seg.to_dict() for seg in segments]


def _segment_confidence(distances: list[float], buffer_m: float) -> float:
    """Calculate confidence score for a segment based on point distances.

    Points very close to the trail get higher confidence.
    Returns 0-100.
    """
    if not distances:
        return 0.0

    # Average distance as fraction of buffer, inverted
    avg_dist = sum(distances) / len(distances)
    if buffer_m <= 0:
        return 100.0

    # Closer = higher confidence
    confidence = max(0.0, (1.0 - avg_dist / buffer_m)) * 100.0
    return confidence
