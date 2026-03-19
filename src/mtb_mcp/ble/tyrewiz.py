"""Quarq TyreWiz BLE tire pressure reader.

Connects to a TyreWiz sensor via BLE and reads pressure/temperature data.
Requires the optional ``bleak`` package; gracefully returns None when
bleak is not installed.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from mtb_mcp.models.sensor import TirePressureReading

logger = structlog.get_logger(__name__)

# TyreWiz uses a custom GATT service for pressure data
TYREWIZ_SERVICE_UUID = "00001523-1212-efde-1523-785feabcd123"
TYREWIZ_PRESSURE_CHAR_UUID = "00001524-1212-efde-1523-785feabcd123"


def _parse_tyrewiz_data(raw: bytes) -> tuple[float | None, float | None]:
    """Parse TyreWiz pressure characteristic data.

    Returns (pressure_bar, temperature_c).
    TyreWiz sends pressure in 1/100 PSI and temperature in 1/10 degC.
    """
    if len(raw) < 4:
        return None, None

    # Pressure: first 2 bytes, little-endian, in 1/100 PSI
    pressure_psi_100 = int.from_bytes(raw[0:2], byteorder="little")
    pressure_bar = (pressure_psi_100 / 100.0) * 0.0689476 if pressure_psi_100 > 0 else None

    # Temperature: bytes 2-3, little-endian, in 1/10 °C
    temp_10 = int.from_bytes(raw[2:4], byteorder="little", signed=True)
    temp_c = temp_10 / 10.0 if temp_10 != 0 else None

    return pressure_bar, temp_c


async def read_tire_pressure(
    address: str, timeout: float = 10.0,
) -> TirePressureReading | None:
    """Read current tire pressure from a TyreWiz sensor.

    Gracefully returns None if bleak is not installed or the sensor
    is unavailable.

    Args:
        address: MAC address / UUID of the TyreWiz sensor.
        timeout: Connection timeout in seconds.

    Returns:
        A TirePressureReading with pressure and temperature, or None.
    """
    try:
        from bleak import BleakClient
    except ImportError:
        logger.warning("bleak_not_installed", hint="Install with: poetry install --with ble")
        return None

    try:
        async with BleakClient(address, timeout=timeout) as client:
            raw = await client.read_gatt_char(TYREWIZ_PRESSURE_CHAR_UUID)
            pressure_bar, temp_c = _parse_tyrewiz_data(raw)

            return TirePressureReading(
                front_bar=pressure_bar,
                rear_bar=None,
                front_temp_c=temp_c,
                rear_temp_c=None,
                timestamp=datetime.now(tz=timezone.utc),
            )
    except Exception as exc:
        logger.error("tyrewiz_read_failed", address=address, error=str(exc))
        return None
