"""BLE cycling sensor discovery.

Scans for nearby BLE devices advertising standard cycling service UUIDs.
Requires the optional ``bleak`` package; gracefully returns an empty list
when bleak is not installed.
"""

from __future__ import annotations

import structlog

from mtb_mcp.models.sensor import BLEDevice, SensorType

logger = structlog.get_logger(__name__)

# Standard BLE Service UUIDs for cycling peripherals
CYCLING_SERVICES: dict[str, SensorType] = {
    "00001816-0000-1000-8000-00805f9b34fb": SensorType.speed_cadence,
    "00001818-0000-1000-8000-00805f9b34fb": SensorType.power_meter,
    "0000180d-0000-1000-8000-00805f9b34fb": SensorType.heart_rate,
}


async def scan_sensors(timeout: float = 10.0) -> list[BLEDevice]:
    """Scan for nearby BLE cycling sensors.

    Returns a list of discovered devices with their sensor type.
    Gracefully returns an empty list if bleak is not installed or
    Bluetooth hardware is unavailable.
    """
    try:
        from bleak import BleakScanner
    except ImportError:
        logger.warning("bleak_not_installed", hint="Install with: poetry install --with ble")
        return []

    try:
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    except Exception as exc:
        logger.error("ble_scan_failed", error=str(exc))
        return []

    results: list[BLEDevice] = []
    for device, adv_data in devices.values():
        # Determine sensor type from advertised service UUIDs
        sensor_type: SensorType | None = None
        service_uuids: list[str] = adv_data.service_uuids or []
        for uuid in service_uuids:
            uuid_lower = uuid.lower()
            if uuid_lower in CYCLING_SERVICES:
                sensor_type = CYCLING_SERVICES[uuid_lower]
                break

        # Only include cycling-related devices
        if sensor_type is not None:
            results.append(BLEDevice(
                name=device.name,
                address=device.address,
                rssi=adv_data.rssi or -100,
                sensor_type=sensor_type,
            ))

    logger.info("ble_scan_complete", found=len(results), timeout=timeout)
    return results
