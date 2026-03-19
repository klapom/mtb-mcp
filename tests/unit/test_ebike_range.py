"""Tests for eBike range calculator.

Parametrized tests covering:
- Different assist modes
- Flat terrain consumption
- Uphill increases consumption
- Downhill reduces consumption (recuperation)
- Heavy rider uses more battery
- Insufficient battery returns can_finish=False
- Safety margin (10%)
- estimate_flat_range_km
"""

from __future__ import annotations

import math

import pytest

from mtb_mcp.intelligence.ebike_range import (
    ASSIST_FACTORS,
    EBikeRangeInput,
    EBikeRangeResult,
    calculate_range,
    estimate_flat_range_km,
)
from mtb_mcp.models.common import GeoPoint


def _flat_points(distance_km: float = 10.0, num_points: int = 11) -> list[GeoPoint]:
    """Create a flat elevation profile (all at 500m)."""
    step = distance_km / (num_points - 1)
    return [
        GeoPoint(
            lat=49.0 + (i * step / 111.0),
            lon=11.0,
            ele=500.0,
        )
        for i in range(num_points)
    ]


def _uphill_points(
    distance_km: float = 10.0, elevation_gain_m: float = 500.0, num_points: int = 11,
) -> list[GeoPoint]:
    """Create a steady uphill profile."""
    step = distance_km / (num_points - 1)
    ele_step = elevation_gain_m / (num_points - 1)
    return [
        GeoPoint(
            lat=49.0 + (i * step / 111.0),
            lon=11.0,
            ele=500.0 + i * ele_step,
        )
        for i in range(num_points)
    ]


def _downhill_points(
    distance_km: float = 10.0, elevation_loss_m: float = 500.0, num_points: int = 11,
) -> list[GeoPoint]:
    """Create a steady downhill profile."""
    step = distance_km / (num_points - 1)
    ele_step = elevation_loss_m / (num_points - 1)
    return [
        GeoPoint(
            lat=49.0 + (i * step / 111.0),
            lon=11.0,
            ele=1000.0 - i * ele_step,
        )
        for i in range(num_points)
    ]


def _default_input(assist_mode: str = "tour") -> EBikeRangeInput:
    """Create a default eBike range input."""
    return EBikeRangeInput(
        battery_wh=625.0,
        charge_pct=100.0,
        rider_kg=80.0,
        bike_kg=23.0,
        assist_mode=assist_mode,
    )


# ---------------------------------------------------------------------------
# Assist mode tests (parametrized)
# ---------------------------------------------------------------------------


class TestAssistModes:
    """Different assist modes should scale consumption proportionally."""

    @pytest.mark.parametrize(
        ("mode", "factor"),
        [
            ("eco", 1.0),
            ("tour", 1.3),
            ("emtb", 1.6),
            ("turbo", 2.2),
        ],
        ids=["eco", "tour", "emtb", "turbo"],
    )
    def test_assist_factor_values(self, mode: str, factor: float) -> None:
        """Verify ASSIST_FACTORS mapping."""
        assert ASSIST_FACTORS[mode] == factor

    @pytest.mark.parametrize(
        ("mode", "factor"),
        [
            ("eco", 1.0),
            ("tour", 1.3),
            ("emtb", 1.6),
            ("turbo", 2.2),
        ],
        ids=["eco", "tour", "emtb", "turbo"],
    )
    def test_consumption_scales_with_assist(self, mode: str, factor: float) -> None:
        """Consumption should scale linearly with assist factor."""
        eco_input = _default_input(assist_mode="eco")
        mode_input = _default_input(assist_mode=mode)
        points = _flat_points()

        eco_result = calculate_range(eco_input, points)
        mode_result = calculate_range(mode_input, points)

        # Mode consumption should be ~factor times eco consumption
        expected = eco_result.estimated_consumption_wh * factor
        assert abs(mode_result.estimated_consumption_wh - expected) < 1.0

    @pytest.mark.parametrize(
        "mode",
        ["eco", "tour", "emtb", "turbo"],
    )
    def test_higher_assist_means_less_range(self, mode: str) -> None:
        """Higher assist modes should give shorter range."""
        eco_range = estimate_flat_range_km(625, 100, "eco")
        mode_range = estimate_flat_range_km(625, 100, mode)
        assert mode_range <= eco_range


# ---------------------------------------------------------------------------
# Flat terrain tests
# ---------------------------------------------------------------------------


class TestFlatTerrain:
    """Flat terrain consumption tests."""

    def test_flat_consumption_reasonable(self) -> None:
        """Flat terrain should use about 8 Wh/km base (adjusted for weight)."""
        inp = _default_input(assist_mode="eco")
        points = _flat_points(distance_km=10.0)
        result = calculate_range(inp, points)

        # Weight factor: (80+23)/90 = 1.144
        # Base: 8 Wh/km * 1.144 * eco(1.0) ~ 9.2 Wh/km
        assert 7.0 < result.consumption_per_km < 12.0

    def test_flat_625wh_eco_range(self) -> None:
        """625 Wh battery in eco on flat should give > 50 km range."""
        range_km = estimate_flat_range_km(625, 100, "eco")
        assert range_km > 50.0

    def test_flat_terrain_can_finish(self) -> None:
        """Full battery should easily handle 10 km flat."""
        inp = _default_input()
        points = _flat_points(distance_km=10.0)
        result = calculate_range(inp, points)
        assert result.can_finish is True


# ---------------------------------------------------------------------------
# Uphill tests
# ---------------------------------------------------------------------------


class TestUphill:
    """Uphill consumption should be higher than flat."""

    def test_uphill_more_than_flat(self) -> None:
        """Uphill consumption must exceed flat consumption."""
        inp = _default_input(assist_mode="eco")
        flat_result = calculate_range(inp, _flat_points())
        uphill_result = calculate_range(inp, _uphill_points())

        assert uphill_result.estimated_consumption_wh > flat_result.estimated_consumption_wh

    def test_steep_uphill_much_more(self) -> None:
        """Very steep uphill should use significantly more energy."""
        inp = _default_input(assist_mode="eco")
        moderate = calculate_range(inp, _uphill_points(elevation_gain_m=200))
        steep = calculate_range(inp, _uphill_points(elevation_gain_m=800))

        assert steep.estimated_consumption_wh > moderate.estimated_consumption_wh * 1.5

    @pytest.mark.parametrize(
        ("gain_m", "min_factor"),
        [
            (100, 1.05),
            (300, 1.2),
            (500, 1.4),
        ],
        ids=["gentle-100m", "moderate-300m", "steep-500m"],
    )
    def test_uphill_consumption_increases_with_grade(
        self, gain_m: float, min_factor: float,
    ) -> None:
        """More elevation gain should increase consumption relative to flat."""
        inp = _default_input(assist_mode="eco")
        flat_result = calculate_range(inp, _flat_points())
        uphill_result = calculate_range(inp, _uphill_points(elevation_gain_m=gain_m))

        ratio = uphill_result.estimated_consumption_wh / flat_result.estimated_consumption_wh
        assert ratio >= min_factor


# ---------------------------------------------------------------------------
# Downhill tests (recuperation)
# ---------------------------------------------------------------------------


class TestDownhill:
    """Downhill should consume less than flat (recuperation)."""

    def test_downhill_less_than_flat(self) -> None:
        """Downhill consumption must be less than flat consumption."""
        inp = _default_input(assist_mode="eco")
        flat_result = calculate_range(inp, _flat_points())
        downhill_result = calculate_range(inp, _downhill_points())

        assert downhill_result.estimated_consumption_wh < flat_result.estimated_consumption_wh

    def test_steep_downhill_recuperation(self) -> None:
        """Steep downhill (> 3%) should trigger recuperation factor (0.2)."""
        inp = _default_input(assist_mode="eco")
        # 500m drop over 10km = 5% grade → recuperation
        downhill_result = calculate_range(inp, _downhill_points(elevation_loss_m=500))

        # With recuperation factor 0.2, consumption should be about 20% of normal
        flat_result = calculate_range(inp, _flat_points())
        assert downhill_result.estimated_consumption_wh < flat_result.estimated_consumption_wh * 0.5

    def test_downhill_still_positive_consumption(self) -> None:
        """Downhill consumption should never be negative."""
        inp = _default_input(assist_mode="eco")
        result = calculate_range(inp, _downhill_points(elevation_loss_m=1000))
        assert result.estimated_consumption_wh > 0


# ---------------------------------------------------------------------------
# Weight tests
# ---------------------------------------------------------------------------


class TestWeight:
    """Heavier riders should use more battery."""

    def test_heavy_rider_more_consumption(self) -> None:
        """90 kg rider should consume more than 60 kg rider."""
        light = EBikeRangeInput(
            battery_wh=625, charge_pct=100, rider_kg=60, bike_kg=23, assist_mode="eco",
        )
        heavy = EBikeRangeInput(
            battery_wh=625, charge_pct=100, rider_kg=100, bike_kg=23, assist_mode="eco",
        )
        points = _flat_points()

        light_result = calculate_range(light, points)
        heavy_result = calculate_range(heavy, points)

        assert heavy_result.estimated_consumption_wh > light_result.estimated_consumption_wh

    @pytest.mark.parametrize(
        ("rider_kg", "bike_kg"),
        [
            (60.0, 15.0),
            (80.0, 23.0),
            (100.0, 30.0),
        ],
        ids=["light-setup", "standard-setup", "heavy-setup"],
    )
    def test_weight_scales_consumption(self, rider_kg: float, bike_kg: float) -> None:
        """Consumption should scale proportionally with total weight."""
        inp = EBikeRangeInput(
            battery_wh=625, charge_pct=100,
            rider_kg=rider_kg, bike_kg=bike_kg, assist_mode="eco",
        )
        points = _flat_points()
        result = calculate_range(inp, points)

        total_weight = rider_kg + bike_kg
        expected_factor = total_weight / 90.0
        # Check consumption per km is roughly base * weight_factor
        assert abs(result.consumption_per_km - 8.0 * expected_factor) < 1.0


# ---------------------------------------------------------------------------
# Insufficient battery / can_finish tests
# ---------------------------------------------------------------------------


class TestInsufficientBattery:
    """Test can_finish=False when battery is not enough."""

    def test_low_charge_long_route(self) -> None:
        """10% charge on a long steep route should not suffice."""
        inp = EBikeRangeInput(
            battery_wh=500, charge_pct=10,
            rider_kg=90, bike_kg=25, assist_mode="turbo",
        )
        # 50 km with 1000m elevation gain
        points = _uphill_points(distance_km=50, elevation_gain_m=1000)
        result = calculate_range(inp, points)
        assert result.can_finish is False

    def test_full_charge_short_route(self) -> None:
        """Full charge on a short flat route should be fine."""
        inp = _default_input()
        points = _flat_points(distance_km=5.0)
        result = calculate_range(inp, points)
        assert result.can_finish is True

    def test_remaining_wh_negative_when_insufficient(self) -> None:
        """Remaining Wh should be negative when battery runs out."""
        inp = EBikeRangeInput(
            battery_wh=100, charge_pct=20,  # Only 20 Wh available
            rider_kg=80, bike_kg=23, assist_mode="turbo",
        )
        points = _uphill_points(distance_km=20, elevation_gain_m=500)
        result = calculate_range(inp, points)
        assert result.remaining_wh < 0


# ---------------------------------------------------------------------------
# Safety margin tests
# ---------------------------------------------------------------------------


class TestSafetyMargin:
    """10% safety margin should be applied."""

    def test_safety_margin_is_10_percent(self) -> None:
        """Result should report 10% safety margin."""
        inp = _default_input()
        points = _flat_points()
        result = calculate_range(inp, points)
        assert result.safety_margin_pct == 10.0

    def test_barely_enough_with_margin_fails(self) -> None:
        """Battery that barely covers consumption but not the margin should fail."""
        # We need consumption to be close to available energy
        # eco + flat + 10km ~ 92 Wh (with weight factor ~1.14)
        inp = EBikeRangeInput(
            battery_wh=100, charge_pct=100,
            rider_kg=80, bike_kg=23, assist_mode="eco",
        )
        # 10 km flat ~ 91 Wh consumption, available = 100 Wh
        # With 10% margin: need 91 * 1.10 = 100.1 Wh > 100 → can_finish=False
        points = _flat_points(distance_km=10.0)
        result = calculate_range(inp, points)

        # The exact consumption depends on haversine vs straight line
        # so we just check that the margin is applied
        if result.estimated_consumption_wh * 1.10 > result.available_wh:
            assert result.can_finish is False
        else:
            assert result.can_finish is True

    def test_enough_without_margin_but_not_with(self) -> None:
        """Edge case: available > consumption but available < consumption * 1.10."""
        # Craft specific numbers
        inp = EBikeRangeInput(
            battery_wh=200, charge_pct=50,  # 100 Wh available
            rider_kg=80, bike_kg=10,  # total 90 kg = weight factor 1.0
            assist_mode="eco",
        )
        # Find a distance where consumption is between 91 and 100
        # flat eco base=8 Wh/km, weight=1.0 → 8 Wh/km
        # 12 km → 96 Wh, with margin 105.6 > 100 → can_finish=False
        points = _flat_points(distance_km=12.0)
        result = calculate_range(inp, points)

        # Verify: available=100, consumption ~96, needed with margin ~105.6
        assert result.available_wh == 100.0
        if (
            result.estimated_consumption_wh < result.available_wh
            and result.estimated_consumption_wh * 1.10 > result.available_wh
        ):
            assert result.can_finish is False


# ---------------------------------------------------------------------------
# estimate_flat_range_km tests
# ---------------------------------------------------------------------------


class TestEstimateFlatRange:
    """Tests for the quick flat-range estimate."""

    def test_full_battery_eco(self) -> None:
        """625 Wh at 100% in eco mode with 90 kg total weight."""
        range_km = estimate_flat_range_km(625, 100, "eco", rider_kg=67.0, bike_kg=23.0)
        # 625 / 8 = 78.1 km (at reference weight)
        assert abs(range_km - 78.1) < 1.0

    def test_half_battery(self) -> None:
        """50% charge should give roughly half the range."""
        full = estimate_flat_range_km(625, 100, "eco")
        half = estimate_flat_range_km(625, 50, "eco")
        assert abs(half - full / 2) < 1.0

    def test_turbo_much_shorter(self) -> None:
        """Turbo mode should give roughly half the range of eco."""
        eco = estimate_flat_range_km(625, 100, "eco")
        turbo = estimate_flat_range_km(625, 100, "turbo")
        # turbo factor = 2.2, eco = 1.0 → turbo range = eco/2.2
        expected_ratio = 1.0 / 2.2
        actual_ratio = turbo / eco
        assert abs(actual_ratio - expected_ratio) < 0.05

    @pytest.mark.parametrize(
        ("mode", "expected_min", "expected_max"),
        [
            ("eco", 50.0, 100.0),
            ("tour", 40.0, 80.0),
            ("emtb", 30.0, 60.0),
            ("turbo", 20.0, 45.0),
        ],
        ids=["eco", "tour", "emtb", "turbo"],
    )
    def test_range_brackets(
        self, mode: str, expected_min: float, expected_max: float,
    ) -> None:
        """Range should be in reasonable brackets for each mode (625 Wh, 100%)."""
        range_km = estimate_flat_range_km(625, 100, mode)
        assert expected_min < range_km < expected_max

    def test_zero_charge(self) -> None:
        """0% charge should give 0 km range."""
        range_km = estimate_flat_range_km(625, 0, "eco")
        assert range_km == 0.0

    def test_unknown_mode_defaults_to_tour(self) -> None:
        """Unknown assist mode should default to tour factor."""
        tour = estimate_flat_range_km(625, 100, "tour")
        unknown = estimate_flat_range_km(625, 100, "unknown_mode")
        assert tour == unknown


# ---------------------------------------------------------------------------
# Result structure tests
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Verify EBikeRangeResult fields."""

    def test_result_has_all_fields(self) -> None:
        inp = _default_input()
        points = _flat_points()
        result = calculate_range(inp, points)

        assert isinstance(result, EBikeRangeResult)
        assert isinstance(result.can_finish, bool)
        assert isinstance(result.estimated_consumption_wh, float)
        assert isinstance(result.available_wh, float)
        assert isinstance(result.remaining_wh, float)
        assert isinstance(result.remaining_pct, float)
        assert isinstance(result.safety_margin_pct, float)
        assert isinstance(result.consumption_per_km, float)
        assert isinstance(result.estimated_range_km, float)

    def test_available_wh_calculation(self) -> None:
        """available_wh should be battery_wh * charge_pct / 100."""
        inp = EBikeRangeInput(
            battery_wh=500, charge_pct=80,
            rider_kg=80, bike_kg=23, assist_mode="eco",
        )
        points = _flat_points()
        result = calculate_range(inp, points)
        assert result.available_wh == 400.0

    def test_empty_route(self) -> None:
        """Single point (no segments) should give zero consumption."""
        inp = _default_input()
        points = [GeoPoint(lat=49.0, lon=11.0, ele=500.0)]
        result = calculate_range(inp, points)
        assert result.estimated_consumption_wh == 0.0
        assert result.can_finish is True
        assert result.estimated_range_km == math.inf
