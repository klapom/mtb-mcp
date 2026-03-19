"""Tests for eBike MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mtb_mcp.tools.ebike_tools import ebike_battery_status, ebike_range_check


class TestEBikeRangeCheckTool:
    """Tests for the ebike_range_check MCP tool."""

    async def test_flat_range_no_coordinates(self) -> None:
        """Should show flat range estimate when no coordinates or distance given."""
        result = await ebike_range_check(
            battery_wh=625, charge_pct=100, assist_mode="eco",
        )

        assert "flat terrain" in result.lower() or "Flat" in result or "flat" in result
        assert "625" in result
        assert "eco" in result

    async def test_manual_distance_elevation(self) -> None:
        """Should calculate range with manual distance and elevation."""
        result = await ebike_range_check(
            battery_wh=625,
            charge_pct=100,
            distance_km=30.0,
            elevation_gain_m=500.0,
            assist_mode="tour",
        )

        assert "eBike Range Check" in result
        assert "tour" in result
        assert "30.0 km" in result

    async def test_manual_distance_flat(self) -> None:
        """Should calculate range with just distance (no elevation)."""
        result = await ebike_range_check(
            battery_wh=625,
            charge_pct=100,
            distance_km=20.0,
            assist_mode="eco",
        )

        assert "eBike Range Check" in result
        assert "YES" in result  # Full battery + flat + eco should be fine

    async def test_insufficient_battery(self) -> None:
        """Low battery + long steep route should fail."""
        result = await ebike_range_check(
            battery_wh=400,
            charge_pct=15,
            distance_km=50.0,
            elevation_gain_m=1500.0,
            rider_kg=100.0,
            bike_kg=28.0,
            assist_mode="turbo",
        )

        assert "NO" in result
        assert "Suggestions" in result

    async def test_invalid_assist_mode(self) -> None:
        """Should reject unknown assist modes."""
        result = await ebike_range_check(assist_mode="rocket")

        assert "Unknown assist mode" in result
        assert "rocket" in result

    @patch("mtb_mcp.tools.ebike_tools.BRouterClient", create=True)
    @patch("mtb_mcp.tools.ebike_tools.get_settings", create=True)
    async def test_route_based_with_brouter_error(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock,
    ) -> None:
        """Should handle BRouter errors gracefully when using coordinates."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"

        mock_client = AsyncMock()
        mock_client.plan_route.side_effect = ConnectionError("BRouter offline")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        result = await ebike_range_check(
            start_lat=49.0, start_lon=11.0,
            end_lat=49.5, end_lon=11.5,
        )

        assert "Could not fetch route" in result or "distance_km" in result

    async def test_zero_distance_error(self) -> None:
        """Should handle zero distance gracefully."""
        result = await ebike_range_check(
            battery_wh=625, charge_pct=100,
            distance_km=0.0,
        )

        assert "Error" in result or "greater than 0" in result

    @pytest.mark.parametrize(
        ("mode", "expect_in_result"),
        [
            ("eco", "eco"),
            ("tour", "tour"),
            ("emtb", "emtb"),
            ("turbo", "turbo"),
        ],
    )
    async def test_assist_modes_in_output(
        self, mode: str, expect_in_result: str,
    ) -> None:
        """Each assist mode should appear in the output."""
        result = await ebike_range_check(
            battery_wh=625, charge_pct=100,
            distance_km=20.0, assist_mode=mode,
        )
        assert expect_in_result in result


class TestEBikeBatteryStatusTool:
    """Tests for the ebike_battery_status MCP tool."""

    async def test_returns_placeholder(self) -> None:
        """Should return placeholder with battery guidance."""
        result = await ebike_battery_status()

        assert "Battery Status" in result
        assert "not yet available" in result
        assert "Bosch" in result

    async def test_lists_common_batteries(self) -> None:
        """Should list common battery models."""
        result = await ebike_battery_status()

        assert "PowerTube 625" in result
        assert "625 Wh" in result
        assert "Shimano" in result

    async def test_provides_usage_guidance(self) -> None:
        """Should guide user to use ebike_range_check."""
        result = await ebike_battery_status()

        assert "ebike_range_check" in result
        assert "battery_wh" in result
        assert "charge_pct" in result
