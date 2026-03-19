"""Standard BLE Heart Rate service reader.

Connects to a BLE heart rate monitor and reads the current HR measurement.
Requires the optional ``bleak`` package; gracefully returns None when
bleak is not installed.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from mtb_mcp.models.sensor import HeartRateReading

logger = structlog.get_logger(__name__)

HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"


def _parse_hr_measurement(raw: bytes) -> tuple[int, list[int] | None]:
    """Parse a BLE Heart Rate Measurement characteristic value.

    Per the Bluetooth Heart Rate Profile specification:
    - Byte 0, bit 0: HR value format (0 = uint8, 1 = uint16)
    - Byte 0, bit 4: RR-Interval present
    - Remaining bytes: HR value, then optional RR intervals (1/1024 s each)

    Returns:
        (bpm, rr_intervals_ms) where rr_intervals_ms may be None.
    """
    flags = raw[0]
    hr_format_16bit = bool(flags & 0x01)
    rr_present = bool(flags & 0x10)

    offset = 1
    if hr_format_16bit:
        bpm = int.from_bytes(raw[offset : offset + 2], byteorder="little")
        offset += 2
    else:
        bpm = raw[offset]
        offset += 1

    rr_intervals_ms: list[int] | None = None
    if rr_present and offset + 1 < len(raw):
        rr_intervals_ms = []
        while offset + 1 < len(raw):
            rr_raw = int.from_bytes(raw[offset : offset + 2], byteorder="little")
            # Convert from 1/1024 seconds to milliseconds
            rr_ms = int(round(rr_raw * 1000 / 1024))
            rr_intervals_ms.append(rr_ms)
            offset += 2

    return bpm, rr_intervals_ms


async def read_heart_rate(
    address: str, timeout: float = 10.0,
) -> HeartRateReading | None:
    """Read current heart rate from a BLE HR sensor.

    Gracefully returns None if bleak is not installed or the sensor
    is unavailable.

    Args:
        address: MAC address / UUID of the HR sensor.
        timeout: Connection timeout in seconds.

    Returns:
        A HeartRateReading with BPM and optional RR intervals, or None.
    """
    try:
        from bleak import BleakClient
    except ImportError:
        logger.warning("bleak_not_installed", hint="Install with: poetry install --with ble")
        return None

    try:
        async with BleakClient(address, timeout=timeout) as client:
            raw = await client.read_gatt_char(HR_MEASUREMENT_UUID)
            bpm, rr_intervals = _parse_hr_measurement(raw)

            return HeartRateReading(
                bpm=bpm,
                rr_intervals_ms=rr_intervals,
                timestamp=datetime.now(tz=timezone.utc),
            )
    except Exception as exc:
        logger.error("hr_read_failed", address=address, error=str(exc))
        return None
