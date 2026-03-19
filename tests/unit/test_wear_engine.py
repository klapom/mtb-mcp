"""Tests for the component wear calculation engine."""

from __future__ import annotations

from datetime import date

import pytest

from mtb_mcp.intelligence.wear_engine import (
    SERVICE_INTERVALS,
    calculate_effective_km,
    calculate_wear_pct,
    get_wear_status,
    km_remaining,
)

# ---------------------------------------------------------------------------
# Terrain modifiers
# ---------------------------------------------------------------------------


class TestTerrainModifiers:
    """Terrain modifiers should scale effective km."""

    @pytest.mark.parametrize(
        ("terrain", "expected_modifier"),
        [
            ("S0", 0.8),
            ("S1", 1.0),
            ("S2", 1.2),
            ("S3", 1.5),
            ("S4", 2.0),
            ("S5", 2.0),
            ("S6", 2.0),
        ],
        ids=["S0-forstweg", "S1-easy", "S2-technical", "S3-demanding",
             "S4-expert", "S5-expert", "S6-expert"],
    )
    def test_terrain_modifier(self, terrain: str, expected_modifier: float) -> None:
        result = calculate_effective_km(100.0, terrain=terrain, weather="dry", avg_power_watts=200.0)
        expected = 100.0 * expected_modifier * 1.0 * 1.0  # weather=dry=1.0, power=200=1.0
        assert result == pytest.approx(expected)

    def test_unknown_terrain_defaults_to_1(self) -> None:
        """Unknown terrain should default to modifier 1.0."""
        result = calculate_effective_km(100.0, terrain="unknown", weather="dry", avg_power_watts=200.0)
        assert result == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Weather modifiers
# ---------------------------------------------------------------------------


class TestWeatherModifiers:
    """Weather modifiers should scale effective km."""

    @pytest.mark.parametrize(
        ("weather", "expected_modifier"),
        [
            ("dry", 1.0),
            ("damp", 1.1),
            ("wet", 1.3),
            ("muddy", 1.8),
        ],
        ids=["dry", "damp", "wet", "muddy"],
    )
    def test_weather_modifier(self, weather: str, expected_modifier: float) -> None:
        result = calculate_effective_km(100.0, terrain="S1", weather=weather, avg_power_watts=200.0)
        expected = 100.0 * 1.0 * expected_modifier * 1.0
        assert result == pytest.approx(expected)

    def test_unknown_weather_defaults_to_1(self) -> None:
        """Unknown weather should default to modifier 1.0."""
        result = calculate_effective_km(100.0, terrain="S1", weather="unknown", avg_power_watts=200.0)
        assert result == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Intensity modifiers
# ---------------------------------------------------------------------------


class TestIntensityModifiers:
    """Power-based intensity modifiers should scale effective km."""

    @pytest.mark.parametrize(
        ("watts", "expected_modifier"),
        [
            (100.0, 0.9),   # < 150W
            (149.9, 0.9),   # just under 150W
            (150.0, 1.0),   # 150-250W
            (200.0, 1.0),   # mid range
            (249.9, 1.0),   # just under 250W
            (250.0, 1.1),   # 250-350W
            (300.0, 1.1),   # mid range
            (349.9, 1.1),   # just under 350W
            (350.0, 1.3),   # > 350W
            (500.0, 1.3),   # well above
        ],
        ids=[
            "100W", "149.9W", "150W", "200W", "249.9W",
            "250W", "300W", "349.9W", "350W", "500W",
        ],
    )
    def test_intensity_modifier(self, watts: float, expected_modifier: float) -> None:
        result = calculate_effective_km(100.0, terrain="S1", weather="dry", avg_power_watts=watts)
        expected = 100.0 * 1.0 * 1.0 * expected_modifier
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Combined effective km
# ---------------------------------------------------------------------------


class TestEffectiveKmCombined:
    """Effective km should combine all modifiers multiplicatively."""

    def test_all_modifiers_combined(self) -> None:
        """S3 terrain, wet weather, high power should stack."""
        result = calculate_effective_km(
            50.0, terrain="S3", weather="wet", avg_power_watts=300.0,
        )
        expected = 50.0 * 1.5 * 1.3 * 1.1
        assert result == pytest.approx(expected)

    def test_zero_km(self) -> None:
        """Zero km should always return zero."""
        result = calculate_effective_km(0.0, terrain="S6", weather="muddy", avg_power_watts=500.0)
        assert result == 0.0

    def test_default_parameters(self) -> None:
        """Default parameters (S1, dry, 200W) should return actual km."""
        result = calculate_effective_km(42.0)
        assert result == pytest.approx(42.0)

    def test_hardest_conditions(self) -> None:
        """S6 + muddy + 500W = maximum effective km."""
        result = calculate_effective_km(10.0, terrain="S6", weather="muddy", avg_power_watts=500.0)
        expected = 10.0 * 2.0 * 1.8 * 1.3
        assert result == pytest.approx(expected)

    def test_easiest_conditions(self) -> None:
        """S0 + dry + 100W = minimum effective km."""
        result = calculate_effective_km(10.0, terrain="S0", weather="dry", avg_power_watts=100.0)
        expected = 10.0 * 0.8 * 1.0 * 0.9
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Wear percentage
# ---------------------------------------------------------------------------


class TestWearPct:
    """Wear percentage calculation tests."""

    def test_km_based_component(self) -> None:
        """Chain at 750 effective km = 50%."""
        pct = calculate_wear_pct(
            effective_km=750.0, hours=0.0,
            installed_date=date(2025, 1, 1),
            component_type="chain",
            reference_date=date(2025, 6, 1),
        )
        assert pct == pytest.approx(50.0)

    def test_hour_based_component(self) -> None:
        """Fork at 100 hours = 50%."""
        pct = calculate_wear_pct(
            effective_km=0.0, hours=100.0,
            installed_date=date(2025, 1, 1),
            component_type="fork",
            reference_date=date(2025, 6, 1),
        )
        assert pct == pytest.approx(50.0)

    def test_time_based_component(self) -> None:
        """Brake fluid at 6 months = 50% (interval = 12 months)."""
        pct = calculate_wear_pct(
            effective_km=0.0, hours=0.0,
            installed_date=date(2025, 1, 15),
            component_type="brake_fluid",
            reference_date=date(2025, 7, 15),
        )
        assert pct == pytest.approx(50.0)

    def test_tubeless_sealant_time_based(self) -> None:
        """Tubeless sealant at 3 months = 50% (interval = 6 months)."""
        pct = calculate_wear_pct(
            effective_km=0.0, hours=0.0,
            installed_date=date(2025, 1, 1),
            component_type="tubeless_sealant",
            reference_date=date(2025, 4, 1),
        )
        assert pct == pytest.approx(50.0)

    def test_overdue_component(self) -> None:
        """Chain at 2000 effective km = 133%."""
        pct = calculate_wear_pct(
            effective_km=2000.0, hours=0.0,
            installed_date=date(2025, 1, 1),
            component_type="chain",
            reference_date=date(2025, 6, 1),
        )
        assert pct == pytest.approx(2000.0 / 1500.0 * 100.0)

    def test_fresh_component(self) -> None:
        """Component at 0 km on install date = 0%."""
        pct = calculate_wear_pct(
            effective_km=0.0, hours=0.0,
            installed_date=date(2025, 6, 1),
            component_type="chain",
            reference_date=date(2025, 6, 1),
        )
        assert pct == pytest.approx(0.0)

    def test_unknown_component_type(self) -> None:
        """Unknown component type returns 0%."""
        pct = calculate_wear_pct(
            effective_km=1000.0, hours=50.0,
            installed_date=date(2025, 1, 1),
            component_type="unknown_part",
            reference_date=date(2025, 6, 1),
        )
        assert pct == 0.0


# ---------------------------------------------------------------------------
# Wear status thresholds
# ---------------------------------------------------------------------------


class TestWearStatus:
    """Wear status thresholds: good <60%, warning 60-85%, critical 85-100%, overdue >100%."""

    @pytest.mark.parametrize(
        ("effective_km", "expected_status"),
        [
            (0.0, "good"),       # 0%
            (500.0, "good"),     # 33%
            (890.0, "good"),     # 59.3%
            (900.0, "warning"),  # 60%
            (1000.0, "warning"), # 66.7%
            (1274.0, "warning"), # 84.9%
            (1275.0, "critical"), # 85%
            (1400.0, "critical"), # 93.3%
            (1500.0, "critical"), # 100% -- at the limit
            (1501.0, "overdue"), # 100.1%
            (2000.0, "overdue"), # 133%
        ],
        ids=[
            "0pct", "33pct", "59pct", "60pct-warning",
            "67pct", "85pct-boundary", "85pct-critical",
            "93pct", "100pct-at-limit", "100.1pct-overdue", "133pct",
        ],
    )
    def test_status_thresholds_km_based(
        self, effective_km: float, expected_status: str,
    ) -> None:
        """Chain service interval = 1500 effective km."""
        status = get_wear_status(
            effective_km=effective_km, hours=0.0,
            installed_date=date(2025, 1, 1),
            component_type="chain",
            reference_date=date(2025, 1, 1),  # avoid time-based wear
        )
        assert status == expected_status

    def test_status_hour_based(self) -> None:
        """Fork at 180 hours = 90% = critical."""
        status = get_wear_status(
            effective_km=0.0, hours=180.0,
            installed_date=date(2025, 1, 1),
            component_type="fork",
            reference_date=date(2025, 1, 1),
        )
        assert status == "critical"

    def test_status_time_based_overdue(self) -> None:
        """Brake fluid after 13 months = overdue."""
        status = get_wear_status(
            effective_km=0.0, hours=0.0,
            installed_date=date(2024, 1, 1),
            component_type="brake_fluid",
            reference_date=date(2025, 2, 2),
        )
        assert status == "overdue"


# ---------------------------------------------------------------------------
# km_remaining
# ---------------------------------------------------------------------------


class TestKmRemaining:
    """Estimated remaining km tests."""

    def test_km_remaining_chain(self) -> None:
        """Chain at 1000 km has 500 km remaining."""
        remaining = km_remaining(1000.0, "chain")
        assert remaining == pytest.approx(500.0)

    def test_km_remaining_at_limit(self) -> None:
        """Chain at 1500 km has 0 remaining."""
        remaining = km_remaining(1500.0, "chain")
        assert remaining == pytest.approx(0.0)

    def test_km_remaining_overdue(self) -> None:
        """Chain at 2000 km still returns 0 (clamped)."""
        remaining = km_remaining(2000.0, "chain")
        assert remaining == pytest.approx(0.0)

    def test_km_remaining_fresh(self) -> None:
        """Fresh component has full interval remaining."""
        remaining = km_remaining(0.0, "chain")
        assert remaining == pytest.approx(1500.0)

    def test_km_remaining_hour_based_returns_none(self) -> None:
        """Hour-based component (fork) returns None for km remaining."""
        remaining = km_remaining(100.0, "fork")
        assert remaining is None

    def test_km_remaining_time_based_returns_none(self) -> None:
        """Time-based component (brake_fluid) returns None."""
        remaining = km_remaining(0.0, "brake_fluid")
        assert remaining is None

    def test_km_remaining_unknown_type(self) -> None:
        """Unknown component type returns None."""
        remaining = km_remaining(100.0, "unknown_part")
        assert remaining is None

    def test_km_remaining_bottom_bracket(self) -> None:
        """Bottom bracket at 3000 km has 2000 km remaining."""
        remaining = km_remaining(3000.0, "bottom_bracket")
        assert remaining == pytest.approx(2000.0)


# ---------------------------------------------------------------------------
# Service interval coverage
# ---------------------------------------------------------------------------


class TestServiceIntervalCoverage:
    """All known component types should have service intervals defined."""

    def test_all_component_types_have_intervals(self) -> None:
        """Every ComponentType should have an entry in SERVICE_INTERVALS."""
        from mtb_mcp.models.bike import ComponentType

        for ct in ComponentType:
            assert ct.value in SERVICE_INTERVALS, (
                f"Missing service interval for {ct.value}"
            )

    def test_all_intervals_have_positive_values(self) -> None:
        """All interval values should be positive (where defined)."""
        for comp_type, (km_val, hours_val, months_val) in SERVICE_INTERVALS.items():
            if km_val is not None:
                assert km_val > 0, f"{comp_type} km interval must be positive"
            if hours_val is not None:
                assert hours_val > 0, f"{comp_type} hours interval must be positive"
            if months_val is not None:
                assert months_val > 0, f"{comp_type} months interval must be positive"
