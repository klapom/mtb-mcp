"""BLE sensor data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SensorType(str, Enum):
    """Supported BLE cycling sensor types."""

    heart_rate = "heart_rate"
    power_meter = "power_meter"
    speed_cadence = "speed_cadence"
    tire_pressure = "tire_pressure"


class BLEDevice(BaseModel):
    """A discovered BLE device with optional sensor classification."""

    name: str | None = None
    address: str = Field(description="MAC address or UUID")
    rssi: int = Field(description="Signal strength in dBm")
    sensor_type: SensorType | None = None


class TirePressureReading(BaseModel):
    """Tire pressure reading from a BLE pressure sensor (e.g. TyreWiz)."""

    front_bar: float | None = None
    rear_bar: float | None = None
    front_temp_c: float | None = None
    rear_temp_c: float | None = None
    timestamp: datetime


class HeartRateReading(BaseModel):
    """Heart rate reading from a standard BLE HR sensor."""

    bpm: int = Field(ge=0, le=300, description="Beats per minute")
    rr_intervals_ms: list[int] | None = None
    timestamp: datetime
