"""Tests for BLE sensor MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from mtb_mcp.models.sensor import BLEDevice, SensorType, TirePressureReading
from mtb_mcp.tools.sensor_tools import sensor_read_pressure, sensor_scan


class TestSensorScanTool:
    """Tests for the sensor_scan MCP tool."""

    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_no_devices_found(self, mock_scan: AsyncMock) -> None:
        """Should show helpful message when no sensors found."""
        mock_scan.return_value = []

        result = await sensor_scan(timeout=5.0)

        assert "No BLE cycling sensors found" in result
        assert "bleak" in result
        mock_scan.assert_called_once_with(timeout=5.0)

    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_devices_found(self, mock_scan: AsyncMock) -> None:
        """Should list discovered devices."""
        mock_scan.return_value = [
            BLEDevice(
                name="Wahoo TICKR",
                address="AA:BB:CC:DD:EE:FF",
                rssi=-55,
                sensor_type=SensorType.heart_rate,
            ),
            BLEDevice(
                name="Quarq DZero",
                address="11:22:33:44:55:66",
                rssi=-70,
                sensor_type=SensorType.power_meter,
            ),
        ]

        result = await sensor_scan()

        assert "2 BLE cycling sensor(s)" in result
        assert "Wahoo TICKR" in result
        assert "heart_rate" in result
        assert "Quarq DZero" in result
        assert "power_meter" in result
        assert "-55 dBm" in result

    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_default_timeout(self, mock_scan: AsyncMock) -> None:
        """Should use default 10s timeout."""
        mock_scan.return_value = []

        await sensor_scan()

        mock_scan.assert_called_once_with(timeout=10.0)


class TestSensorReadPressureTool:
    """Tests for the sensor_read_pressure MCP tool."""

    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_no_tyrewiz_found(self, mock_scan: AsyncMock) -> None:
        """Should show helpful message when no TyreWiz found."""
        mock_scan.return_value = []

        result = await sensor_read_pressure()

        assert "No TyreWiz sensors found" in result

    @patch("mtb_mcp.tools.sensor_tools.read_tire_pressure")
    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_tyrewiz_reading(
        self, mock_scan: AsyncMock, mock_read: AsyncMock,
    ) -> None:
        """Should read and display pressure from TyreWiz sensors."""
        from datetime import datetime, timezone

        mock_scan.return_value = [
            BLEDevice(
                name="TyreWiz Front",
                address="AA:BB:CC:DD:EE:FF",
                rssi=-50,
                sensor_type=SensorType.tire_pressure,
            ),
        ]
        mock_read.return_value = TirePressureReading(
            front_bar=1.8,
            rear_bar=None,
            front_temp_c=25.0,
            rear_temp_c=None,
            timestamp=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
        )

        result = await sensor_read_pressure()

        assert "Tire Pressure Readings" in result
        assert "1.80 bar" in result
        assert "25.0 C" in result

    @patch("mtb_mcp.tools.sensor_tools.read_tire_pressure")
    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_tyrewiz_connection_failed(
        self, mock_scan: AsyncMock, mock_read: AsyncMock,
    ) -> None:
        """Should handle failed connection gracefully."""
        mock_scan.return_value = [
            BLEDevice(
                name="TyreWiz Front",
                address="AA:BB:CC:DD:EE:FF",
                rssi=-50,
                sensor_type=SensorType.tire_pressure,
            ),
        ]
        mock_read.return_value = None

        result = await sensor_read_pressure()

        assert "Connection failed" in result

    @patch("mtb_mcp.tools.sensor_tools.scan_sensors")
    async def test_non_tyrewiz_devices_ignored(self, mock_scan: AsyncMock) -> None:
        """Should ignore non-TyreWiz sensor devices."""
        mock_scan.return_value = [
            BLEDevice(
                name="Wahoo TICKR",
                address="AA:BB:CC:DD:EE:FF",
                rssi=-55,
                sensor_type=SensorType.heart_rate,
            ),
        ]

        result = await sensor_read_pressure()

        assert "No TyreWiz sensors found" in result
