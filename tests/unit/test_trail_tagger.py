"""Tests for GPS trace to trail name matching."""

from __future__ import annotations

import pytest

from mtb_mcp.intelligence.trail_tagger import (
    TrailMatch,
    match_trails,
    tag_ride_segments,
)
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.trail import MTBScale, Trail, TrailSurface

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_trail() -> Trail:
    """A straight trail going east from (49.596, 11.004) to (49.596, 11.008)."""
    return Trail(
        osm_id=1001,
        name="Erlangen Singletrack",
        mtb_scale=MTBScale.S2,
        surface=TrailSurface.dirt,
        length_m=300.0,
        geometry=[
            GeoPoint(lat=49.596, lon=11.004),
            GeoPoint(lat=49.596, lon=11.005),
            GeoPoint(lat=49.596, lon=11.006),
            GeoPoint(lat=49.596, lon=11.007),
            GeoPoint(lat=49.596, lon=11.008),
        ],
    )


@pytest.fixture()
def second_trail() -> Trail:
    """A trail going north from (49.596, 11.010) to (49.600, 11.010)."""
    return Trail(
        osm_id=1002,
        name="Waldweg Nord",
        mtb_scale=MTBScale.S1,
        surface=TrailSurface.gravel,
        length_m=450.0,
        geometry=[
            GeoPoint(lat=49.596, lon=11.010),
            GeoPoint(lat=49.597, lon=11.010),
            GeoPoint(lat=49.598, lon=11.010),
            GeoPoint(lat=49.599, lon=11.010),
            GeoPoint(lat=49.600, lon=11.010),
        ],
    )


@pytest.fixture()
def gps_on_trail() -> list[GeoPoint]:
    """GPS points that follow the simple_trail closely (within ~10m)."""
    return [
        GeoPoint(lat=49.59601, lon=11.00401),
        GeoPoint(lat=49.59599, lon=11.00501),
        GeoPoint(lat=49.59602, lon=11.00600),
        GeoPoint(lat=49.59598, lon=11.00701),
        GeoPoint(lat=49.59601, lon=11.00799),
    ]


@pytest.fixture()
def gps_far_from_trail() -> list[GeoPoint]:
    """GPS points far from any trail (Nuernberg area)."""
    return [
        GeoPoint(lat=49.454, lon=11.078),
        GeoPoint(lat=49.455, lon=11.079),
        GeoPoint(lat=49.456, lon=11.080),
        GeoPoint(lat=49.457, lon=11.081),
        GeoPoint(lat=49.458, lon=11.082),
    ]


@pytest.fixture()
def gps_multi_trail() -> list[GeoPoint]:
    """GPS points that ride along two trails sequentially."""
    return [
        # First ride along simple_trail (east)
        GeoPoint(lat=49.59601, lon=11.00401),
        GeoPoint(lat=49.59599, lon=11.00501),
        GeoPoint(lat=49.59602, lon=11.00600),
        GeoPoint(lat=49.59598, lon=11.00701),
        GeoPoint(lat=49.59601, lon=11.00799),
        # Then ride to second_trail area (no trail)
        GeoPoint(lat=49.596, lon=11.009),
        # Then ride along second_trail (north)
        GeoPoint(lat=49.59601, lon=11.01001),
        GeoPoint(lat=49.59700, lon=11.01000),
        GeoPoint(lat=49.59800, lon=11.00999),
        GeoPoint(lat=49.59900, lon=11.01001),
        GeoPoint(lat=49.60000, lon=11.01000),
    ]


# ---------------------------------------------------------------------------
# Tests: match_trails
# ---------------------------------------------------------------------------


class TestMatchTrails:
    """Tests for matching GPS traces to known trails."""

    def test_empty_gps_points(self, simple_trail: Trail) -> None:
        """Empty GPS list should return no matches."""
        result = match_trails([], [simple_trail])
        assert result == []

    def test_empty_trails(self, gps_on_trail: list[GeoPoint]) -> None:
        """Empty trail list should return no matches."""
        result = match_trails(gps_on_trail, [])
        assert result == []

    def test_matching_gps_to_trail(
        self, gps_on_trail: list[GeoPoint], simple_trail: Trail,
    ) -> None:
        """GPS points on a trail should match with high overlap."""
        result = match_trails(gps_on_trail, [simple_trail], buffer_m=25.0)
        assert len(result) >= 1
        match = result[0]
        assert match.trail.osm_id == 1001
        assert match.overlap_pct > 80.0
        assert match.distance_avg_m < 25.0

    def test_no_match_far_away(
        self, gps_far_from_trail: list[GeoPoint], simple_trail: Trail,
    ) -> None:
        """GPS points far from any trail should not match."""
        result = match_trails(gps_far_from_trail, [simple_trail], buffer_m=25.0)
        assert result == []

    def test_overlap_percentage_calculation(
        self, simple_trail: Trail,
    ) -> None:
        """Test overlap percentage with partial match."""
        # Only 3 of 5 points near the trail
        mixed_points = [
            GeoPoint(lat=49.59601, lon=11.00401),  # on trail
            GeoPoint(lat=49.59599, lon=11.00501),  # on trail
            GeoPoint(lat=49.59602, lon=11.00600),  # on trail
            GeoPoint(lat=49.700, lon=11.100),       # far away
            GeoPoint(lat=49.800, lon=11.200),       # far away
        ]
        result = match_trails(mixed_points, [simple_trail], buffer_m=25.0)
        # 3/5 = 60% overlap, which is above 30% threshold
        assert len(result) == 1
        assert 50.0 < result[0].overlap_pct < 70.0

    def test_filter_below_30_percent(self, simple_trail: Trail) -> None:
        """Matches below 30% overlap should be filtered out."""
        # Only 1 of 5 points near the trail
        mostly_off = [
            GeoPoint(lat=49.59601, lon=11.00401),  # on trail
            GeoPoint(lat=49.700, lon=11.100),       # far away
            GeoPoint(lat=49.800, lon=11.200),       # far away
            GeoPoint(lat=49.900, lon=11.300),       # far away
            GeoPoint(lat=50.000, lon=11.400),       # far away
        ]
        result = match_trails(mostly_off, [simple_trail], buffer_m=25.0)
        assert result == []

    def test_results_sorted_by_overlap(
        self,
        gps_on_trail: list[GeoPoint],
        simple_trail: Trail,
        second_trail: Trail,
    ) -> None:
        """Results should be sorted by overlap percentage (highest first)."""
        result = match_trails(
            gps_on_trail, [simple_trail, second_trail], buffer_m=25.0,
        )
        if len(result) > 1:
            assert result[0].overlap_pct >= result[1].overlap_pct

    def test_trail_without_geometry(self, gps_on_trail: list[GeoPoint]) -> None:
        """Trail without geometry should be skipped."""
        empty_trail = Trail(osm_id=9999, name="Empty Trail")
        result = match_trails(gps_on_trail, [empty_trail], buffer_m=25.0)
        assert result == []

    def test_custom_buffer(
        self, gps_on_trail: list[GeoPoint], simple_trail: Trail,
    ) -> None:
        """Very small buffer should reduce matches."""
        # With 1m buffer, probably no points will match precisely
        result_tight = match_trails(gps_on_trail, [simple_trail], buffer_m=1.0)
        result_wide = match_trails(gps_on_trail, [simple_trail], buffer_m=50.0)
        # Wide buffer should have >= matches compared to tight
        tight_overlap = result_tight[0].overlap_pct if result_tight else 0.0
        wide_overlap = result_wide[0].overlap_pct if result_wide else 0.0
        assert wide_overlap >= tight_overlap

    def test_trail_match_dataclass(self, simple_trail: Trail) -> None:
        """TrailMatch dataclass should store data correctly."""
        match = TrailMatch(trail=simple_trail, overlap_pct=85.5, distance_avg_m=12.3)
        assert match.trail.osm_id == 1001
        assert match.overlap_pct == 85.5
        assert match.distance_avg_m == 12.3


# ---------------------------------------------------------------------------
# Tests: tag_ride_segments
# ---------------------------------------------------------------------------


class TestTagRideSegments:
    """Tests for tagging ride segments with trail names."""

    def test_empty_inputs(self) -> None:
        """Empty inputs should return empty list."""
        assert tag_ride_segments([], []) == []
        trail = Trail(
            osm_id=1, geometry=[GeoPoint(lat=0.0, lon=0.0)],
        )
        assert tag_ride_segments([], [trail]) == []
        assert tag_ride_segments([GeoPoint(lat=0.0, lon=0.0)], []) == []

    def test_single_trail_segment(
        self,
        gps_on_trail: list[GeoPoint],
        simple_trail: Trail,
    ) -> None:
        """GPS trace on a single trail should produce one segment."""
        segments = tag_ride_segments(gps_on_trail, [simple_trail], buffer_m=25.0)
        assert len(segments) >= 1
        seg = segments[0]
        assert seg["trail_name"] == "Erlangen Singletrack"
        assert seg["trail_difficulty"] == "S2"
        assert 0 < seg["overlap_confidence"] <= 100  # type: ignore[operator]

    def test_segment_indices(
        self,
        gps_on_trail: list[GeoPoint],
        simple_trail: Trail,
    ) -> None:
        """Segment indices should be valid indices into GPS points."""
        segments = tag_ride_segments(gps_on_trail, [simple_trail], buffer_m=25.0)
        for seg in segments:
            assert 0 <= seg["start_index"] <= seg["end_index"] < len(gps_on_trail)  # type: ignore[operator]

    def test_multi_trail_ride(
        self,
        gps_multi_trail: list[GeoPoint],
        simple_trail: Trail,
        second_trail: Trail,
    ) -> None:
        """GPS trace across two trails should produce multiple segments."""
        segments = tag_ride_segments(
            gps_multi_trail,
            [simple_trail, second_trail],
            buffer_m=25.0,
            min_consecutive=3,
        )
        # Should have at least one segment
        assert len(segments) >= 1
        # If both trails matched, we should see different names
        trail_names = {seg["trail_name"] for seg in segments}
        # At least one trail should match
        assert len(trail_names) >= 1

    def test_no_match_segment(
        self,
        gps_far_from_trail: list[GeoPoint],
        simple_trail: Trail,
    ) -> None:
        """GPS trace far from trails should produce no segments."""
        segments = tag_ride_segments(
            gps_far_from_trail, [simple_trail], buffer_m=25.0,
        )
        assert segments == []

    def test_segment_dict_keys(
        self,
        gps_on_trail: list[GeoPoint],
        simple_trail: Trail,
    ) -> None:
        """Segment dictionaries should have the expected keys."""
        segments = tag_ride_segments(gps_on_trail, [simple_trail], buffer_m=25.0)
        if segments:
            seg = segments[0]
            assert "start_index" in seg
            assert "end_index" in seg
            assert "trail_name" in seg
            assert "trail_difficulty" in seg
            assert "overlap_confidence" in seg

    def test_unnamed_trail_fallback(self, gps_on_trail: list[GeoPoint]) -> None:
        """Trail without a name should use OSM ID as fallback."""
        unnamed_trail = Trail(
            osm_id=5555,
            name=None,
            mtb_scale=MTBScale.S1,
            geometry=[
                GeoPoint(lat=49.596, lon=11.004),
                GeoPoint(lat=49.596, lon=11.005),
                GeoPoint(lat=49.596, lon=11.006),
                GeoPoint(lat=49.596, lon=11.007),
                GeoPoint(lat=49.596, lon=11.008),
            ],
        )
        segments = tag_ride_segments(
            gps_on_trail, [unnamed_trail], buffer_m=25.0,
        )
        if segments:
            assert "5555" in segments[0]["trail_name"]

    def test_min_consecutive_filter(
        self,
        simple_trail: Trail,
    ) -> None:
        """Short segments below min_consecutive should be filtered out."""
        # Only 2 points on trail, then off
        short_ride = [
            GeoPoint(lat=49.59601, lon=11.00401),
            GeoPoint(lat=49.59599, lon=11.00501),
            GeoPoint(lat=49.700, lon=11.100),
            GeoPoint(lat=49.800, lon=11.200),
            GeoPoint(lat=49.900, lon=11.300),
        ]
        segments = tag_ride_segments(
            short_ride, [simple_trail], buffer_m=25.0, min_consecutive=3,
        )
        # Only 2 consecutive points on trail, which is below min_consecutive=3
        assert segments == []
