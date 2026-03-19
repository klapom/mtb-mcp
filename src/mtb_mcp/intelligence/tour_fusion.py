"""Multi-source tour deduplication and enrichment."""

from __future__ import annotations

import re
import unicodedata

from mtb_mcp.models.tour import TourDetail, TourDifficulty, TourSummary
from mtb_mcp.utils.geo import haversine


def fuzzy_name_match(name1: str, name2: str) -> float:
    """Simple fuzzy name matching score (0-1).

    Approach: Normalize (lowercase, remove special chars),
    then compute Jaccard similarity on word sets.
    Returns 0.0 if both names are empty.
    """
    normalized1 = _normalize_name(name1)
    normalized2 = _normalize_name(name2)

    words1 = set(normalized1.split())
    words2 = set(normalized2.split())

    if not words1 and not words2:
        return 0.0
    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def _normalize_name(name: str) -> str:
    """Normalize a tour name for comparison.

    Lowercase, strip accents, remove non-alphanumeric chars (except spaces).
    """
    # Lowercase
    name = name.lower().strip()
    # Strip accents: NFD decompose, remove combining characters
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Remove non-alphanumeric except spaces
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _is_duplicate_pair(
    a: TourSummary,
    b: TourSummary,
    distance_threshold_m: float,
    length_tolerance_pct: float,
) -> bool:
    """Check if two tours are likely the same tour from different sources.

    Match criteria:
    - Start points within distance_threshold_m
    - Total distance within length_tolerance_pct percent
    - Fuzzy name match (optional, helps break ties)
    """
    # Both must have start points to compare geographically
    if a.start_point is not None and b.start_point is not None:
        dist_km = haversine(
            a.start_point.lat, a.start_point.lon,
            b.start_point.lat, b.start_point.lon,
        )
        dist_m = dist_km * 1000.0
        if dist_m > distance_threshold_m:
            return False
    else:
        # Without start points, rely on name matching only
        name_score = fuzzy_name_match(a.name, b.name)
        return name_score >= 0.7

    # Check distance similarity if both have distance
    if a.distance_km is not None and b.distance_km is not None:
        avg_dist = (a.distance_km + b.distance_km) / 2.0
        if avg_dist > 0:
            pct_diff = abs(a.distance_km - b.distance_km) / avg_dist * 100.0
            if pct_diff > length_tolerance_pct:
                return False

    # Name similarity as additional confirmation (not required, but strengthens match)
    name_score = fuzzy_name_match(a.name, b.name)

    # If names are very different but geo matches, still consider duplicate
    # if both start_point and distance matched
    return not (name_score < 0.1 and (a.distance_km is None or b.distance_km is None))


def _tour_detail_score(tour: TourSummary) -> int:
    """Score a tour by how much detail it has. Higher is better."""
    score = 0
    if tour.distance_km is not None:
        score += 1
    if tour.elevation_m is not None:
        score += 1
    if tour.difficulty is not None:
        score += 1
    if tour.region is not None:
        score += 1
    if tour.url is not None:
        score += 1
    if tour.start_point is not None:
        score += 1

    # TourDetail has extra fields
    if isinstance(tour, TourDetail):
        if tour.description:
            score += 2
        if tour.surfaces:
            score += 1
        if tour.waypoints:
            score += len(tour.waypoints) // 10 + 1
        if tour.rating is not None:
            score += 1
        if tour.download_count is not None:
            score += 1
        if tour.duration_minutes is not None:
            score += 1

    return score


def deduplicate_tours(
    tours: list[TourSummary],
    distance_threshold_m: float = 500.0,
    length_tolerance_pct: float = 10.0,
) -> list[TourSummary]:
    """Remove duplicate tours from multiple sources.

    Match criteria:
    - Start points within distance_threshold_m
    - Total distance within length_tolerance_pct percent
    - Fuzzy name match (optional, helps break ties)

    When duplicates found, keep the one with more details.
    """
    if not tours:
        return []

    # Track which tours are kept vs merged away
    merged: list[bool] = [False] * len(tours)
    result: list[TourSummary] = []

    for i in range(len(tours)):
        if merged[i]:
            continue

        best = tours[i]
        best_score = _tour_detail_score(best)

        for j in range(i + 1, len(tours)):
            if merged[j]:
                continue

            if _is_duplicate_pair(
                best, tours[j], distance_threshold_m, length_tolerance_pct
            ):
                merged[j] = True
                j_score = _tour_detail_score(tours[j])
                if j_score > best_score:
                    best = tours[j]
                    best_score = j_score

        result.append(best)

    return result


def merge_tour_details(tours: list[TourDetail]) -> TourDetail:
    """Merge details from multiple sources for the same tour.

    Strategy:
    - Keep best description (longest)
    - Merge surfaces lists
    - Keep most waypoints
    - Prefer rating from source with more reviews
    """
    if not tours:
        msg = "Cannot merge empty tour list"
        raise ValueError(msg)

    if len(tours) == 1:
        return tours[0]

    # Start with the tour that has the highest detail score
    base = max(tours, key=_tour_detail_score)

    # Best description (longest non-None)
    best_description: str | None = None
    for t in tours:
        if t.description is not None and (
            best_description is None or len(t.description) > len(best_description)
        ):
            best_description = t.description

    # Merge surfaces (union of all unique surfaces)
    all_surfaces: list[str] = []
    seen_surfaces: set[str] = set()
    for t in tours:
        for s in t.surfaces:
            if s not in seen_surfaces:
                seen_surfaces.add(s)
                all_surfaces.append(s)

    # Keep most waypoints
    best_waypoints = base.waypoints
    for t in tours:
        if len(t.waypoints) > len(best_waypoints):
            best_waypoints = t.waypoints

    # Prefer rating from source with more downloads (proxy for reviews)
    best_rating = base.rating
    best_download_count = base.download_count or 0
    for t in tours:
        if t.rating is not None:
            t_downloads = t.download_count or 0
            if t_downloads > best_download_count:
                best_rating = t.rating
                best_download_count = t_downloads

    # Best distance (prefer non-None, then most precise)
    best_distance = base.distance_km
    for t in tours:
        if t.distance_km is not None and best_distance is None:
            best_distance = t.distance_km

    # Best elevation
    best_elevation = base.elevation_m
    for t in tours:
        if t.elevation_m is not None and best_elevation is None:
            best_elevation = t.elevation_m

    # Best difficulty
    best_difficulty = base.difficulty
    for t in tours:
        if t.difficulty is not None and best_difficulty is None:
            best_difficulty = t.difficulty

    # Best duration
    best_duration = base.duration_minutes
    for t in tours:
        if t.duration_minutes is not None and best_duration is None:
            best_duration = t.duration_minutes

    return TourDetail(
        id=base.id,
        source=base.source,
        name=base.name,
        distance_km=best_distance,
        elevation_m=best_elevation,
        difficulty=best_difficulty,
        region=base.region or next((t.region for t in tours if t.region), None),
        url=base.url,
        start_point=base.start_point or next(
            (t.start_point for t in tours if t.start_point is not None), None
        ),
        description=best_description,
        duration_minutes=best_duration,
        surfaces=all_surfaces,
        waypoints=best_waypoints,
        download_count=best_download_count if best_download_count > 0 else None,
        rating=best_rating,
    )


def rank_tours(
    tours: list[TourSummary],
    preference_distance_km: float | None = None,
    preference_difficulty: str | None = None,
) -> list[TourSummary]:
    """Rank tours by relevance to user preferences.

    Tours are scored based on how well they match the preferences.
    Higher score = more relevant. Ties broken by detail score.
    """
    if not tours:
        return []

    # Parse difficulty preference
    pref_diff: TourDifficulty | None = None
    if preference_difficulty is not None:
        try:
            pref_diff = TourDifficulty(preference_difficulty.lower())
        except ValueError:
            pref_diff = None

    difficulty_order: dict[TourDifficulty, int] = {
        TourDifficulty.easy: 0,
        TourDifficulty.moderate: 1,
        TourDifficulty.difficult: 2,
        TourDifficulty.expert: 3,
    }

    def _score(tour: TourSummary) -> float:
        score = 0.0

        # Distance preference scoring
        if preference_distance_km is not None and tour.distance_km is not None:
            dist_diff = abs(tour.distance_km - preference_distance_km)
            # Normalize: 0 diff = 100 points, falls off linearly
            max_penalty = preference_distance_km * 0.5
            if max_penalty > 0:
                score += max(0.0, 100.0 * (1.0 - dist_diff / max_penalty))

        # Difficulty preference scoring
        if pref_diff is not None and tour.difficulty is not None:
            pref_idx = difficulty_order.get(pref_diff, 1)
            tour_idx = difficulty_order.get(tour.difficulty, 1)
            diff = abs(pref_idx - tour_idx)
            # Exact match = 100, one off = 50, two off = 0
            score += max(0.0, 100.0 - diff * 50.0)

        # Bonus for having more details
        score += _tour_detail_score(tour) * 2.0

        return score

    scored = sorted(tours, key=_score, reverse=True)
    return scored
