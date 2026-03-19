"""MCP tools for BLE cycling sensors."""

from __future__ import annotations

import structlog

from mtb_mcp.ble.scanner import scan_sensors
from mtb_mcp.ble.tyrewiz import read_tire_pressure
from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)


def _bar_to_psi(bar: float) -> float:
    """Convert bar to PSI."""
    return round(bar * 14.5038, 1)


@mcp.tool()
async def sensor_scan(timeout: float = 10.0) -> str:
    """Scan for nearby BLE cycling sensors (heart rate, power, speed/cadence, tire pressure).

    Requires Bluetooth hardware. Returns discovered devices with signal strength.
    Install the optional BLE group for hardware support: poetry install --with ble
    """
    devices = await scan_sensors(timeout=timeout)

    if not devices:
        return (
            "No BLE cycling sensors found.\n"
            "Possible reasons:\n"
            "  - No Bluetooth hardware available\n"
            "  - bleak package not installed (run: poetry install --with ble)\n"
            "  - No sensors in range or sensors not advertising\n"
            f"  - Scan timeout too short ({timeout}s)"
        )

    lines = [f"Found {len(devices)} BLE cycling sensor(s):", ""]

    for device in sorted(devices, key=lambda d: d.rssi, reverse=True):
        name = device.name or "Unknown"
        sensor_label = device.sensor_type.value if device.sensor_type else "unknown"
        lines.append(f"  {name}")
        lines.append(f"    Address: {device.address}")
        lines.append(f"    Type: {sensor_label}")
        lines.append(f"    Signal: {device.rssi} dBm")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def sensor_read_pressure() -> str:
    """Read current tire pressure from Quarq TyreWiz sensors.

    Returns front and rear pressure in bar and PSI.
    Requires Bluetooth hardware and bleak package.
    Note: Currently reads from a single sensor -- specify the address in the future.
    """
    # For now, scan for TyreWiz sensors first
    devices = await scan_sensors(timeout=5.0)

    tyrewiz_devices = [
        d for d in devices
        if d.sensor_type is not None
        and d.name is not None
        and "tyrewiz" in d.name.lower()
    ]

    if not tyrewiz_devices:
        return (
            "No TyreWiz sensors found.\n"
            "Make sure your TyreWiz sensors are powered on and in range.\n"
            "If bleak is not installed, run: poetry install --with ble"
        )

    lines = ["Tire Pressure Readings:", ""]

    for device in tyrewiz_devices:
        reading = await read_tire_pressure(device.address, timeout=10.0)
        if reading is None:
            lines.append(f"  {device.name}: Connection failed")
            continue

        if reading.front_bar is not None:
            psi = _bar_to_psi(reading.front_bar)
            lines.append(f"  {device.name}:")
            lines.append(f"    Pressure: {reading.front_bar:.2f} bar ({psi} PSI)")
            if reading.front_temp_c is not None:
                lines.append(f"    Temperature: {reading.front_temp_c:.1f} C")
        else:
            lines.append(f"  {device.name}: No pressure data available")

    return "\n".join(lines)
