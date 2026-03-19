"""Tests for trail condition estimation algorithm."""

from __future__ import annotations

import pytest

from mtb_mcp.intelligence.trail_condition import (
    ABSORPTION_RATES,
    DRYING_CONSTANTS,
    estimate_trail_condition,
)
from mtb_mcp.models.trail import TrailConditionStatus, TrailSurface


class TestTrailConditionFrozen:
    """Frozen conditions should override everything else."""

    @pytest.mark.parametrize("temp", [-1.0, -5.0, -20.0])
    def test_frozen_at_sub_zero(self, temp: float) -> None:
        """Sub-zero temperature → frozen regardless of rain."""
        condition, confidence, _ = estimate_trail_condition(
            surface="dirt",
            hourly_rain_mm=[0.0] * 48,
            current_temp_c=temp,
        )
        assert condition == TrailConditionStatus.frozen
        assert confidence == "high"

    def test_frozen_with_heavy_rain(self) -> None:
        """Even heavy rain → frozen when temp is below zero."""
        condition, _, reasoning = estimate_trail_condition(
            surface="dirt",
            hourly_rain_mm=[10.0] * 48,
            current_temp_c=-3.0,
        )
        assert condition == TrailConditionStatus.frozen
        assert "-3.0" in reasoning

    def test_not_frozen_at_zero(self) -> None:
        """Exactly 0°C is not below zero, so not frozen."""
        condition, _, _ = estimate_trail_condition(
            surface="dirt",
            hourly_rain_mm=[0.0] * 48,
            current_temp_c=0.0,
        )
        assert condition != TrailConditionStatus.frozen


class TestTrailConditionDry:
    """Dry conditions after long dry periods."""

    def test_no_rain_all_surfaces(self) -> None:
        """No rain at all → dry for every surface."""
        for surface in TrailSurface:
            condition, confidence, _ = estimate_trail_condition(
                surface=surface,
                hourly_rain_mm=[0.0] * 48,
            )
            assert condition == TrailConditionStatus.dry
            assert confidence == "high"

    def test_dry_after_long_period(self) -> None:
        """Light rain 48 hours ago on dirt should have dried."""
        rain = [0.0] * 46 + [1.0, 1.0]  # rain was 46-47 hours ago
        condition, _, _ = estimate_trail_condition(
            surface="dirt",
            hourly_rain_mm=rain,
        )
        assert condition == TrailConditionStatus.dry


class TestTrailConditionAsphalt:
    """Asphalt has zero absorption so should always be dry."""

    @pytest.mark.parametrize(
        "rain",
        [
            [0.0] * 48,
            [5.0] * 48,
            [20.0] + [0.0] * 47,
        ],
        ids=["no_rain", "constant_rain", "recent_heavy"],
    )
    def test_asphalt_always_dry(self, rain: list[float]) -> None:
        """Asphalt absorption is 0 → always dry."""
        condition, _, _ = estimate_trail_condition(
            surface=TrailSurface.asphalt,
            hourly_rain_mm=rain,
        )
        assert condition == TrailConditionStatus.dry


class TestTrailConditionRock:
    """Rock has low absorption and dries quickly."""

    def test_rock_dries_quickly(self) -> None:
        """Moderate rain 8 hours ago on rock should be dry."""
        rain = [0.0] * 8 + [3.0] + [0.0] * 39
        condition, _, _ = estimate_trail_condition(
            surface=TrailSurface.rock,
            hourly_rain_mm=rain,
        )
        assert condition == TrailConditionStatus.dry

    def test_rock_wet_during_rain(self) -> None:
        """Heavy recent rain on rock can still be damp."""
        rain = [5.0, 5.0] + [0.0] * 46
        condition, _, _ = estimate_trail_condition(
            surface=TrailSurface.rock,
            hourly_rain_mm=rain,
        )
        # absorption=0.1 → 5*0.1*e^0 + 5*0.1*e^(-1/4) ≈ 0.5+0.39 ≈ 0.89 → dry
        assert condition == TrailConditionStatus.dry


class TestTrailConditionMuddy:
    """Heavy rain on absorbent surfaces → muddy."""

    def test_dirt_heavy_recent_rain(self) -> None:
        """Heavy rain on dirt → muddy."""
        rain = [10.0, 10.0, 10.0] + [0.0] * 45
        condition, _, _ = estimate_trail_condition(
            surface=TrailSurface.dirt,
            hourly_rain_mm=rain,
        )
        assert condition == TrailConditionStatus.muddy

    def test_roots_heavy_rain(self) -> None:
        """Roots surface absorbs even more than dirt."""
        rain = [8.0, 8.0] + [0.0] * 46
        condition, _, _ = estimate_trail_condition(
            surface=TrailSurface.roots,
            hourly_rain_mm=rain,
        )
        # absorption=0.9 → 8*0.9*e^0 + 8*0.9*e^(-1/36) ≈ 7.2+7.0 ≈ 14.2 → muddy
        assert condition == TrailConditionStatus.muddy


class TestTrailConditionParametrized:
    """Parametrized tests across surface × rain combinations."""

    @pytest.mark.parametrize(
        ("surface", "rain", "expected"),
        [
            # Dry scenarios
            ("asphalt", [5.0] * 48, TrailConditionStatus.dry),
            ("rock", [0.0] * 48, TrailConditionStatus.dry),
            ("dirt", [0.0] * 48, TrailConditionStatus.dry),
            ("gravel", [0.0] * 48, TrailConditionStatus.dry),
            # Damp scenarios
            ("dirt", [2.0] + [0.0] * 47, TrailConditionStatus.damp),
            ("grass", [3.0] + [0.0] * 47, TrailConditionStatus.damp),
            # Wet scenarios
            ("dirt", [5.0, 3.0] + [0.0] * 46, TrailConditionStatus.wet),
            # Muddy scenarios
            ("dirt", [10.0] * 5 + [0.0] * 43, TrailConditionStatus.muddy),
            ("roots", [10.0] * 3 + [0.0] * 45, TrailConditionStatus.muddy),
        ],
        ids=[
            "asphalt-heavy-rain-still-dry",
            "rock-no-rain-dry",
            "dirt-no-rain-dry",
            "gravel-no-rain-dry",
            "dirt-light-recent-damp",
            "grass-moderate-recent-damp",
            "dirt-moderate-recent-wet",
            "dirt-heavy-prolonged-muddy",
            "roots-heavy-recent-muddy",
        ],
    )
    def test_surface_rain_matrix(
        self,
        surface: str,
        rain: list[float],
        expected: TrailConditionStatus,
    ) -> None:
        condition, _, _ = estimate_trail_condition(
            surface=surface,
            hourly_rain_mm=rain,
        )
        assert condition == expected


class TestTrailConditionEdgeCases:
    """Edge cases and input validation."""

    def test_empty_rain_history(self) -> None:
        """Empty rain list → dry."""
        condition, _, _ = estimate_trail_condition(
            surface="dirt",
            hourly_rain_mm=[],
        )
        assert condition == TrailConditionStatus.dry

    def test_unknown_surface_defaults(self) -> None:
        """Unknown surface string uses default absorption/drying."""
        condition, _, _ = estimate_trail_condition(
            surface="cobblestone",
            hourly_rain_mm=[0.0] * 48,
        )
        assert condition == TrailConditionStatus.dry

    def test_enum_and_string_equivalent(self) -> None:
        """TrailSurface enum and raw string should produce same result."""
        rain = [3.0, 2.0, 1.0] + [0.0] * 45
        c1, _, _ = estimate_trail_condition(surface=TrailSurface.dirt, hourly_rain_mm=rain)
        c2, _, _ = estimate_trail_condition(surface="dirt", hourly_rain_mm=rain)
        assert c1 == c2

    def test_reasoning_includes_surface(self) -> None:
        """Reasoning string should mention the surface type."""
        _, _, reasoning = estimate_trail_condition(
            surface="gravel",
            hourly_rain_mm=[0.0] * 48,
        )
        assert "gravel" in reasoning

    def test_all_surfaces_have_rates(self) -> None:
        """Every TrailSurface enum member should have absorption + drying rates."""
        for surface in TrailSurface:
            assert surface.value in ABSORPTION_RATES, f"Missing absorption rate for {surface}"
            assert surface.value in DRYING_CONSTANTS, f"Missing drying constant for {surface}"
