"""Tests for the ride score algorithm."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mtb_mcp.intelligence.ride_score import (
    RideScoreInput,
    RideScoreResult,
    calculate_ride_score,
)


def _perfect_input() -> RideScoreInput:
    """Create an input that should yield a perfect score."""
    now = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
    return RideScoreInput(
        temp_c=20.0,
        wind_speed_kmh=5.0,
        wind_gust_kmh=10.0,
        precipitation_probability=0.0,
        precipitation_mm=0.0,
        humidity_pct=50.0,
        trail_condition="dry",
        ride_start=now,
        ride_duration_hours=2.0,
        sunrise=now.replace(hour=5),
        sunset=now.replace(hour=21),
    )


class TestRideScorePerfect:
    """Perfect conditions should yield 100."""

    def test_perfect_score(self) -> None:
        result = calculate_ride_score(_perfect_input())
        assert result.score == 100
        assert result.verdict == "Perfect"
        assert result.weather_score == 40
        assert result.trail_score == 30
        assert result.wind_score == 15
        assert result.daylight_score == 15
        assert result.factors == []


class TestRideScoreWeather:
    """Weather sub-score tests (0-40)."""

    @pytest.mark.parametrize(
        ("temp_c", "expected_penalty"),
        [
            (1.0, 20),   # < 2°C → extreme
            (-5.0, 20),  # < 2°C → extreme
            (36.0, 20),  # > 35°C → extreme
            (4.0, 10),   # < 5°C → uncomfortable
            (33.0, 10),  # > 32°C → uncomfortable
            (20.0, 0),   # comfortable → no penalty
        ],
        ids=["cold-extreme", "freezing", "hot-extreme", "cold-moderate", "hot-moderate", "ok"],
    )
    def test_temperature_penalties(self, temp_c: float, expected_penalty: int) -> None:
        inp = _perfect_input()
        inp.temp_c = temp_c
        result = calculate_ride_score(inp)
        assert result.weather_score == 40 - expected_penalty

    @pytest.mark.parametrize(
        ("prob", "expected_penalty"),
        [
            (90.0, 30),
            (81.0, 30),
            (60.0, 15),
            (51.0, 15),
            (49.0, 0),
            (0.0, 0),
        ],
        ids=["90pct", "81pct", "60pct", "51pct", "49pct", "0pct"],
    )
    def test_rain_probability_penalties(self, prob: float, expected_penalty: int) -> None:
        inp = _perfect_input()
        inp.precipitation_probability = prob
        result = calculate_ride_score(inp)
        assert result.weather_score == 40 - expected_penalty

    def test_heavy_precipitation_penalty(self) -> None:
        inp = _perfect_input()
        inp.precipitation_mm = 10.0
        result = calculate_ride_score(inp)
        assert result.weather_score == 40 - 20

    def test_high_humidity_penalty(self) -> None:
        inp = _perfect_input()
        inp.humidity_pct = 95.0
        result = calculate_ride_score(inp)
        assert result.weather_score == 40 - 5

    def test_combined_weather_penalties(self) -> None:
        """Multiple weather penalties should stack."""
        inp = _perfect_input()
        inp.temp_c = 1.0  # -20
        inp.precipitation_probability = 90.0  # -30
        result = calculate_ride_score(inp)
        # 40 - 20 - 30 = -10 → clamped to 0
        assert result.weather_score == 0

    def test_weather_score_floor(self) -> None:
        """Weather score cannot go below 0."""
        inp = _perfect_input()
        inp.temp_c = -10.0
        inp.precipitation_probability = 100.0
        inp.precipitation_mm = 20.0
        inp.humidity_pct = 95.0
        result = calculate_ride_score(inp)
        assert result.weather_score == 0


class TestRideScoreTrail:
    """Trail sub-score tests (0-30)."""

    @pytest.mark.parametrize(
        ("condition", "expected"),
        [
            ("dry", 30),
            ("damp", 20),
            ("wet", 10),
            ("muddy", 0),
            ("frozen", 5),
        ],
    )
    def test_trail_condition_scores(self, condition: str, expected: int) -> None:
        inp = _perfect_input()
        inp.trail_condition = condition
        result = calculate_ride_score(inp)
        assert result.trail_score == expected

    def test_unknown_trail_condition_default(self) -> None:
        """Unknown trail condition should default to 15."""
        inp = _perfect_input()
        inp.trail_condition = "unknown"
        result = calculate_ride_score(inp)
        assert result.trail_score == 15


class TestRideScoreWind:
    """Wind sub-score tests (0-15)."""

    @pytest.mark.parametrize(
        ("speed", "expected"),
        [
            (5.0, 15),
            (14.9, 15),
            (15.0, 10),
            (24.9, 10),
            (25.0, 5),
            (39.9, 5),
            (40.0, 2),
            (54.9, 2),
            (55.0, 0),
            (80.0, 0),
        ],
        ids=[
            "calm", "just-under-15", "at-15", "just-under-25",
            "at-25", "just-under-40", "at-40", "just-under-55",
            "at-55", "storm",
        ],
    )
    def test_wind_speed_brackets(self, speed: float, expected: int) -> None:
        inp = _perfect_input()
        inp.wind_speed_kmh = speed
        result = calculate_ride_score(inp)
        assert result.wind_score == expected

    def test_gust_penalty(self) -> None:
        """Gusts > 60 km/h → extra -5 penalty."""
        inp = _perfect_input()
        inp.wind_speed_kmh = 10.0  # base 15
        inp.wind_gust_kmh = 65.0
        result = calculate_ride_score(inp)
        assert result.wind_score == 10  # 15 - 5

    def test_gust_penalty_no_negative(self) -> None:
        """Gust penalty should not make wind score negative."""
        inp = _perfect_input()
        inp.wind_speed_kmh = 55.0  # base 0
        inp.wind_gust_kmh = 80.0  # -5
        result = calculate_ride_score(inp)
        assert result.wind_score == 0


class TestRideScoreDaylight:
    """Daylight sub-score tests (0-15)."""

    def test_full_daylight(self) -> None:
        """Ride entirely within daylight → 15."""
        result = calculate_ride_score(_perfect_input())
        assert result.daylight_score == 15

    def test_night_ride(self) -> None:
        """Ride entirely at night → 0."""
        inp = _perfect_input()
        inp.ride_start = datetime(2025, 7, 15, 22, 0, tzinfo=timezone.utc)
        inp.sunrise = datetime(2025, 7, 15, 6, 0, tzinfo=timezone.utc)
        inp.sunset = datetime(2025, 7, 15, 20, 0, tzinfo=timezone.utc)
        result = calculate_ride_score(inp)
        assert result.daylight_score == 0

    def test_partial_daylight(self) -> None:
        """Ride half in daylight → ~8."""
        inp = _perfect_input()
        # 2h ride starting 1h before sunset → 1h daylight / 2h total = 50%
        inp.ride_start = datetime(2025, 7, 15, 19, 0, tzinfo=timezone.utc)
        inp.sunset = datetime(2025, 7, 15, 20, 0, tzinfo=timezone.utc)
        inp.sunrise = datetime(2025, 7, 15, 6, 0, tzinfo=timezone.utc)
        inp.ride_duration_hours = 2.0
        result = calculate_ride_score(inp)
        assert result.daylight_score == 8  # round(15 * 0.5) = 8

    def test_no_times_provided(self) -> None:
        """Missing sunrise/sunset → assume full daylight (15)."""
        inp = _perfect_input()
        inp.ride_start = None
        inp.sunrise = None
        inp.sunset = None
        result = calculate_ride_score(inp)
        assert result.daylight_score == 15

    def test_dawn_ride(self) -> None:
        """Ride starting before sunrise → partial daylight."""
        inp = _perfect_input()
        inp.ride_start = datetime(2025, 7, 15, 5, 0, tzinfo=timezone.utc)
        inp.sunrise = datetime(2025, 7, 15, 6, 0, tzinfo=timezone.utc)
        inp.sunset = datetime(2025, 7, 15, 20, 0, tzinfo=timezone.utc)
        inp.ride_duration_hours = 2.0
        # 1h dark + 1h light → 50% daylight
        result = calculate_ride_score(inp)
        assert result.daylight_score == 8


class TestRideScoreVerdict:
    """Verdict mapping tests."""

    @pytest.mark.parametrize(
        ("adjustments", "expected_verdict"),
        [
            # 40+30+15+15=100
            ({}, "Perfect"),
            # weather=30(temp 4C -10), trail=20(damp), wind=15, daylight=15 = 80 -> Perfect
            # Need lower: weather=40, trail=20(damp), wind=5(25kmh), daylight=15 = 80 -> Perfect
            # So: weather=30(-10), trail=20(damp), wind=15, daylight=15 = 80 -> still Perfect
            # 40+20+5(wind 30)+15 = 80 -> still Perfect
            # 40+20+5(wind 30)+0(night) = 65 -> Good
            (
                {
                    "trail_condition": "damp",
                    "wind_speed_kmh": 30.0,
                    "ride_start": datetime(2025, 7, 15, 22, 0, tzinfo=timezone.utc),
                },
                "Good",
            ),
            # weather=30(-10), trail=10(wet), wind=5(30kmh), daylight=15 = 60 -> still Good
            # weather=40, trail=10(wet), wind=5(30kmh), daylight=0(night) = 55 -> Fair
            (
                {
                    "trail_condition": "wet",
                    "wind_speed_kmh": 30.0,
                    "ride_start": datetime(2025, 7, 15, 22, 0, tzinfo=timezone.utc),
                },
                "Fair",
            ),
            # weather=20(-20 extreme temp), trail=0(muddy), wind=15, daylight=0(night)=35
            (
                {
                    "trail_condition": "muddy",
                    "temp_c": 1.0,
                    "ride_start": datetime(2025, 7, 15, 22, 0, tzinfo=timezone.utc),
                },
                "Poor",
            ),
            (
                {
                    "trail_condition": "muddy",
                    "temp_c": 1.0,
                    "precipitation_probability": 90.0,
                    "wind_speed_kmh": 60.0,
                },
                "Stay Home",
            ),
        ],
        ids=["perfect", "good", "fair", "poor", "stay-home"],
    )
    def test_verdict_mapping(
        self, adjustments: dict[str, object], expected_verdict: str
    ) -> None:
        inp = _perfect_input()
        for key, value in adjustments.items():
            setattr(inp, key, value)
        result = calculate_ride_score(inp)
        assert result.verdict == expected_verdict


class TestRideScoreFactors:
    """Factor explanations should be present for each penalty."""

    def test_no_factors_on_perfect(self) -> None:
        result = calculate_ride_score(_perfect_input())
        assert result.factors == []

    def test_factors_present_on_penalties(self) -> None:
        inp = _perfect_input()
        inp.temp_c = 1.0
        inp.wind_speed_kmh = 50.0
        result = calculate_ride_score(inp)
        assert len(result.factors) >= 2


class TestRideScoreTotalRange:
    """Score should always be in [0, 100]."""

    def test_score_upper_bound(self) -> None:
        result = calculate_ride_score(_perfect_input())
        assert 0 <= result.score <= 100

    def test_score_lower_bound_extreme(self) -> None:
        inp = _perfect_input()
        inp.temp_c = -20.0
        inp.precipitation_probability = 100.0
        inp.precipitation_mm = 50.0
        inp.humidity_pct = 100.0
        inp.trail_condition = "muddy"
        inp.wind_speed_kmh = 100.0
        inp.wind_gust_kmh = 100.0
        # Night ride
        inp.ride_start = datetime(2025, 7, 15, 23, 0, tzinfo=timezone.utc)
        inp.sunrise = datetime(2025, 7, 15, 6, 0, tzinfo=timezone.utc)
        inp.sunset = datetime(2025, 7, 15, 20, 0, tzinfo=timezone.utc)
        result = calculate_ride_score(inp)
        assert result.score == 0


class TestRideScoreResult:
    """RideScoreResult dataclass sanity checks."""

    def test_result_fields(self) -> None:
        result = calculate_ride_score(_perfect_input())
        assert isinstance(result, RideScoreResult)
        assert isinstance(result.score, int)
        assert isinstance(result.verdict, str)
        assert isinstance(result.factors, list)
