"""Tests for BLE sensor data models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mtb_mcp.models.sensor import (
    BLEDevice,
    HeartRateReading,
    SensorType,
    TirePressureReading,
)


class TestSensorType:
    """SensorType enum tests."""

    def test_heart_rate_value(self) -> None:
        assert SensorType.heart_rate.value == "heart_rate"

    def test_power_meter_value(self) -> None:
        assert SensorType.power_meter.value == "power_meter"

    def test_speed_cadence_value(self) -> None:
        assert SensorType.speed_cadence.value == "speed_cadence"

    def test_tire_pressure_value(self) -> None:
        assert SensorType.tire_pressure.value == "tire_pressure"

    def test_from_string(self) -> None:
        assert SensorType("heart_rate") is SensorType.heart_rate

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid"):
            SensorType("invalid")


class TestBLEDevice:
    """BLEDevice model tests."""

    def test_minimal_device(self) -> None:
        device = BLEDevice(address="AA:BB:CC:DD:EE:FF", rssi=-65)
        assert device.address == "AA:BB:CC:DD:EE:FF"
        assert device.rssi == -65
        assert device.name is None
        assert device.sensor_type is None

    def test_full_device(self) -> None:
        device = BLEDevice(
            name="Wahoo TICKR",
            address="AA:BB:CC:DD:EE:FF",
            rssi=-42,
            sensor_type=SensorType.heart_rate,
        )
        assert device.name == "Wahoo TICKR"
        assert device.sensor_type == SensorType.heart_rate

    def test_device_serialization(self) -> None:
        device = BLEDevice(
            name="Power Meter",
            address="11:22:33:44:55:66",
            rssi=-70,
            sensor_type=SensorType.power_meter,
        )
        data = device.model_dump()
        assert data["name"] == "Power Meter"
        assert data["sensor_type"] == "power_meter"


class TestTirePressureReading:
    """TirePressureReading model tests."""

    def test_full_reading(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        reading = TirePressureReading(
            front_bar=1.8,
            rear_bar=2.0,
            front_temp_c=25.5,
            rear_temp_c=26.0,
            timestamp=ts,
        )
        assert reading.front_bar == 1.8
        assert reading.rear_bar == 2.0
        assert reading.front_temp_c == 25.5
        assert reading.rear_temp_c == 26.0
        assert reading.timestamp == ts

    def test_partial_reading(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        reading = TirePressureReading(
            front_bar=1.5,
            timestamp=ts,
        )
        assert reading.front_bar == 1.5
        assert reading.rear_bar is None
        assert reading.front_temp_c is None
        assert reading.rear_temp_c is None

    def test_serialization_roundtrip(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        reading = TirePressureReading(front_bar=1.8, rear_bar=2.0, timestamp=ts)
        data = reading.model_dump()
        restored = TirePressureReading.model_validate(data)
        assert restored.front_bar == reading.front_bar
        assert restored.rear_bar == reading.rear_bar


class TestHeartRateReading:
    """HeartRateReading model tests."""

    def test_simple_reading(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        reading = HeartRateReading(bpm=142, timestamp=ts)
        assert reading.bpm == 142
        assert reading.rr_intervals_ms is None

    def test_reading_with_rr(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        reading = HeartRateReading(
            bpm=150,
            rr_intervals_ms=[400, 410, 395],
            timestamp=ts,
        )
        assert reading.rr_intervals_ms == [400, 410, 395]

    def test_bpm_validation_too_high(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            HeartRateReading(bpm=301, timestamp=ts)

    def test_bpm_validation_negative(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            HeartRateReading(bpm=-1, timestamp=ts)

    def test_bpm_boundary_values(self) -> None:
        ts = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        reading_min = HeartRateReading(bpm=0, timestamp=ts)
        reading_max = HeartRateReading(bpm=300, timestamp=ts)
        assert reading_min.bpm == 0
        assert reading_max.bpm == 300
