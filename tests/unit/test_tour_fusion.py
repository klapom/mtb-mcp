"""Tests for multi-source tour deduplication and enrichment."""

from __future__ import annotations

import pytest

from mtb_mcp.intelligence.tour_fusion import (
    deduplicate_tours,
    fuzzy_name_match,
    merge_tour_details,
    rank_tours,
)
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.tour import TourDetail, TourDifficulty, TourSource, TourSummary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def komoot_tour() -> TourSummary:
    """A tour from Komoot near Erlangen."""
    return TourSummary(
        id="komoot-100",
        source=TourSource.komoot,
        name="Erlangen Forest Loop",
        distance_km=32.5,
        elevation_m=450.0,
        difficulty=TourDifficulty.moderate,
        region="Mittelfranken",
        url="https://www.komoot.de/tour/100",
        start_point=GeoPoint(lat=49.596, lon=11.004),
    )


@pytest.fixture()
def gpstour_duplicate() -> TourSummary:
    """A duplicate of the Komoot tour from GPS-Tour.info (same route, different source)."""
    return TourSummary(
        id="gpstour-200",
        source=TourSource.gps_tour,
        name="Erlangen Forest Trail Loop",
        distance_km=33.0,
        elevation_m=445.0,
        difficulty=TourDifficulty.moderate,
        url="https://www.gps-tour.info/de/touren/detail.200.html",
        start_point=GeoPoint(lat=49.597, lon=11.005),
    )


@pytest.fixture()
def unique_tour() -> TourSummary:
    """A completely different tour."""
    return TourSummary(
        id="komoot-300",
        source=TourSource.komoot,
        name="Nuernberg City Ride",
        distance_km=18.0,
        elevation_m=120.0,
        difficulty=TourDifficulty.easy,
        region="Nuernberg",
        start_point=GeoPoint(lat=49.454, lon=11.078),
    )


@pytest.fixture()
def komoot_detail() -> TourDetail:
    """Detailed Komoot tour."""
    return TourDetail(
        id="komoot-100",
        source=TourSource.komoot,
        name="Erlangen Forest Loop",
        distance_km=32.5,
        elevation_m=450.0,
        difficulty=TourDifficulty.moderate,
        description="A beautiful loop through the forests around Erlangen.",
        surfaces=["gravel", "singletrack"],
        waypoints=[
            GeoPoint(lat=49.596, lon=11.004),
            GeoPoint(lat=49.600, lon=11.010),
            GeoPoint(lat=49.605, lon=11.015),
        ],
        rating=4.2,
        download_count=50,
        start_point=GeoPoint(lat=49.596, lon=11.004),
    )


@pytest.fixture()
def gpstour_detail() -> TourDetail:
    """Detailed GPS-Tour.info tour (same route, different source)."""
    return TourDetail(
        id="gpstour-200",
        source=TourSource.gps_tour,
        name="Erlangen Wald-Runde",
        distance_km=33.0,
        elevation_m=445.0,
        difficulty=TourDifficulty.moderate,
        description=(
            "Eine wunderschoene Runde durch die Waelder rund um Erlangen. "
            "Die Tour fuehrt ueber schoene Waldwege und bietet tolle Ausblicke."
        ),
        surfaces=["dirt", "roots"],
        waypoints=[
            GeoPoint(lat=49.597, lon=11.005),
            GeoPoint(lat=49.601, lon=11.011),
        ],
        rating=4.5,
        download_count=120,
        start_point=GeoPoint(lat=49.597, lon=11.005),
    )


# ---------------------------------------------------------------------------
# Tests: fuzzy_name_match
# ---------------------------------------------------------------------------


class TestFuzzyNameMatch:
    """Tests for Jaccard-based fuzzy name matching."""

    def test_identical_names(self) -> None:
        """Identical names should score 1.0."""
        assert fuzzy_name_match("Erlangen Loop", "Erlangen Loop") == 1.0

    def test_case_insensitive(self) -> None:
        """Matching should be case-insensitive."""
        assert fuzzy_name_match("Erlangen Loop", "erlangen loop") == 1.0

    def test_partial_overlap(self) -> None:
        """Partially overlapping names should score between 0 and 1."""
        score = fuzzy_name_match("Erlangen Forest Loop", "Erlangen Forest Trail Loop")
        assert 0.5 < score < 1.0

    def test_no_overlap(self) -> None:
        """Completely different names should score 0."""
        assert fuzzy_name_match("Erlangen Loop", "Munich City Tour") == 0.0

    def test_empty_names(self) -> None:
        """Empty names should score 0."""
        assert fuzzy_name_match("", "") == 0.0
        assert fuzzy_name_match("Test", "") == 0.0
        assert fuzzy_name_match("", "Test") == 0.0

    def test_special_characters_stripped(self) -> None:
        """Special characters should be stripped for comparison."""
        score = fuzzy_name_match("Erlangen (Forest) Loop!", "Erlangen Forest Loop")
        assert score == 1.0

    def test_accented_characters(self) -> None:
        """Accented characters should be normalized."""
        score = fuzzy_name_match("N\u00fcrnberg Tolle Runde", "Nurnberg Tolle Runde")
        assert score >= 0.5


# ---------------------------------------------------------------------------
# Tests: deduplicate_tours
# ---------------------------------------------------------------------------


class TestDeduplicateTours:
    """Tests for tour deduplication."""

    def test_empty_list(self) -> None:
        """Empty list should return empty."""
        assert deduplicate_tours([]) == []

    def test_single_tour(self) -> None:
        """Single tour should be preserved."""
        tour = TourSummary(
            id="1", source=TourSource.komoot, name="Test",
            distance_km=10.0,
            start_point=GeoPoint(lat=49.5, lon=11.0),
        )
        result = deduplicate_tours([tour])
        assert len(result) == 1
        assert result[0].id == "1"

    def test_removes_duplicates(
        self, komoot_tour: TourSummary, gpstour_duplicate: TourSummary,
    ) -> None:
        """Duplicate tours from different sources should be merged."""
        result = deduplicate_tours([komoot_tour, gpstour_duplicate])
        assert len(result) == 1

    def test_keeps_tour_with_more_details(
        self, komoot_tour: TourSummary, gpstour_duplicate: TourSummary,
    ) -> None:
        """Should keep the tour with more details."""
        result = deduplicate_tours([komoot_tour, gpstour_duplicate])
        assert len(result) == 1
        # komoot_tour has region which gpstour_duplicate doesn't
        assert result[0].region == "Mittelfranken"

    def test_preserves_unique_tours(
        self,
        komoot_tour: TourSummary,
        gpstour_duplicate: TourSummary,
        unique_tour: TourSummary,
    ) -> None:
        """Unique tours should be preserved alongside deduplicated ones."""
        result = deduplicate_tours([komoot_tour, gpstour_duplicate, unique_tour])
        assert len(result) == 2

    def test_no_false_duplicates_different_distance(self) -> None:
        """Tours at same location but very different distances are not duplicates."""
        tour1 = TourSummary(
            id="1", source=TourSource.komoot, name="Short Loop",
            distance_km=10.0,
            start_point=GeoPoint(lat=49.5, lon=11.0),
        )
        tour2 = TourSummary(
            id="2", source=TourSource.gps_tour, name="Long Loop",
            distance_km=50.0,
            start_point=GeoPoint(lat=49.5, lon=11.0),
        )
        result = deduplicate_tours([tour1, tour2])
        assert len(result) == 2

    def test_no_false_duplicates_far_apart(self) -> None:
        """Tours that are far apart should not be considered duplicates."""
        tour1 = TourSummary(
            id="1", source=TourSource.komoot, name="Erlangen Loop",
            distance_km=30.0,
            start_point=GeoPoint(lat=49.596, lon=11.004),
        )
        tour2 = TourSummary(
            id="2", source=TourSource.gps_tour, name="Munich Loop",
            distance_km=30.0,
            start_point=GeoPoint(lat=48.137, lon=11.575),
        )
        result = deduplicate_tours([tour1, tour2])
        assert len(result) == 2

    def test_custom_thresholds(self) -> None:
        """Custom distance and length thresholds should be respected."""
        tour1 = TourSummary(
            id="1", source=TourSource.komoot, name="Trail A",
            distance_km=30.0,
            start_point=GeoPoint(lat=49.596, lon=11.004),
        )
        tour2 = TourSummary(
            id="2", source=TourSource.gps_tour, name="Trail A Variation",
            distance_km=33.5,
            start_point=GeoPoint(lat=49.597, lon=11.005),
        )
        # Strict threshold: 5% tolerance
        result_strict = deduplicate_tours(
            [tour1, tour2], length_tolerance_pct=5.0,
        )
        assert len(result_strict) == 2

        # Relaxed threshold: 20% tolerance
        result_relaxed = deduplicate_tours(
            [tour1, tour2], length_tolerance_pct=20.0,
        )
        assert len(result_relaxed) == 1


# ---------------------------------------------------------------------------
# Tests: merge_tour_details
# ---------------------------------------------------------------------------


class TestMergeTourDetails:
    """Tests for merging tour details from multiple sources."""

    def test_single_tour(self, komoot_detail: TourDetail) -> None:
        """Single tour should be returned as-is."""
        result = merge_tour_details([komoot_detail])
        assert result.id == komoot_detail.id

    def test_empty_raises_error(self) -> None:
        """Empty tour list should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot merge empty tour list"):
            merge_tour_details([])

    def test_keeps_longest_description(
        self, komoot_detail: TourDetail, gpstour_detail: TourDetail,
    ) -> None:
        """Should keep the longest description."""
        result = merge_tour_details([komoot_detail, gpstour_detail])
        # gpstour_detail has a longer description
        assert result.description is not None
        assert len(result.description) > len(komoot_detail.description or "")

    def test_merges_surfaces(
        self, komoot_detail: TourDetail, gpstour_detail: TourDetail,
    ) -> None:
        """Should merge surfaces from both sources (union)."""
        result = merge_tour_details([komoot_detail, gpstour_detail])
        assert "gravel" in result.surfaces
        assert "singletrack" in result.surfaces
        assert "dirt" in result.surfaces
        assert "roots" in result.surfaces

    def test_keeps_most_waypoints(
        self, komoot_detail: TourDetail, gpstour_detail: TourDetail,
    ) -> None:
        """Should keep the set with more waypoints."""
        result = merge_tour_details([komoot_detail, gpstour_detail])
        # komoot_detail has 3 waypoints, gpstour_detail has 2
        assert len(result.waypoints) == 3

    def test_prefers_rating_with_more_downloads(
        self, komoot_detail: TourDetail, gpstour_detail: TourDetail,
    ) -> None:
        """Should prefer rating from source with more downloads."""
        result = merge_tour_details([komoot_detail, gpstour_detail])
        # gpstour_detail has 120 downloads vs komoot_detail's 50
        assert result.rating == 4.5
        assert result.download_count == 120


# ---------------------------------------------------------------------------
# Tests: rank_tours
# ---------------------------------------------------------------------------


class TestRankTours:
    """Tests for tour ranking by preferences."""

    def test_empty_list(self) -> None:
        """Empty list should return empty."""
        assert rank_tours([]) == []

    def test_no_preferences(
        self, komoot_tour: TourSummary, unique_tour: TourSummary,
    ) -> None:
        """Without preferences, should still return all tours."""
        result = rank_tours([komoot_tour, unique_tour])
        assert len(result) == 2

    def test_distance_preference(self) -> None:
        """Tours closer to preferred distance should rank higher."""
        short = TourSummary(
            id="1", source=TourSource.komoot, name="Short",
            distance_km=10.0,
        )
        medium = TourSummary(
            id="2", source=TourSource.komoot, name="Medium",
            distance_km=30.0,
        )
        long = TourSummary(
            id="3", source=TourSource.komoot, name="Long",
            distance_km=60.0,
        )
        result = rank_tours(
            [short, long, medium], preference_distance_km=30.0,
        )
        # Medium (30km) should be first since it matches the preference exactly
        assert result[0].id == "2"

    def test_difficulty_preference(self) -> None:
        """Tours matching difficulty preference should rank higher."""
        easy = TourSummary(
            id="1", source=TourSource.komoot, name="Easy",
            difficulty=TourDifficulty.easy,
        )
        moderate = TourSummary(
            id="2", source=TourSource.komoot, name="Moderate",
            difficulty=TourDifficulty.moderate,
        )
        expert = TourSummary(
            id="3", source=TourSource.komoot, name="Expert",
            difficulty=TourDifficulty.expert,
        )
        result = rank_tours(
            [easy, expert, moderate], preference_difficulty="moderate",
        )
        # Moderate should rank first
        assert result[0].id == "2"

    def test_combined_preferences(self) -> None:
        """Combined distance and difficulty preferences should work together."""
        tour_a = TourSummary(
            id="a", source=TourSource.komoot, name="Tour A",
            distance_km=30.0, difficulty=TourDifficulty.moderate,
        )
        tour_b = TourSummary(
            id="b", source=TourSource.komoot, name="Tour B",
            distance_km=10.0, difficulty=TourDifficulty.expert,
        )
        result = rank_tours(
            [tour_b, tour_a],
            preference_distance_km=30.0,
            preference_difficulty="moderate",
        )
        assert result[0].id == "a"
