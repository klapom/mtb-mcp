"""MCP tools for bike maintenance tracking.

Provides tools to manage bikes, track component wear, log rides,
and record maintenance services.
"""

from __future__ import annotations

import structlog

from mtb_mcp.config import get_settings
from mtb_mcp.intelligence.wear_engine import (
    SERVICE_INTERVALS,
    calculate_effective_km,
    calculate_wear_pct,
    get_wear_status,
    km_remaining,
)
from mtb_mcp.models.bike import ComponentType
from mtb_mcp.server import mcp
from mtb_mcp.storage.bike_garage import BikeGarage
from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)


async def _get_garage() -> tuple[Database, BikeGarage]:
    """Initialize a Database and BikeGarage from settings.

    Returns:
        A tuple of (Database, BikeGarage). Caller must close the database.
    """
    settings = get_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db, BikeGarage(db)


async def _get_or_create_bike(
    garage: BikeGarage, bike_name: str,
) -> tuple[str, bool]:
    """Find a bike by name, creating it if it doesn't exist.

    Args:
        garage: The BikeGarage instance.
        bike_name: Name of the bike.

    Returns:
        Tuple of (bike_id, was_created).
    """
    bike = await garage.get_bike_by_name(bike_name)
    if bike is not None:
        return bike.id, False

    new_bike = await garage.add_bike(bike_name)
    return new_bike.id, True


def _format_component_type(ct: str) -> str:
    """Format a component type for display."""
    return ct.replace("_", " ").title()


@mcp.tool()
async def bike_add_component(
    bike_name: str,
    component_type: str,
    brand: str | None = None,
    model: str | None = None,
) -> str:
    """Add a component to your bike for wear tracking.

    Component types: chain, cassette, brake_pads_front, brake_pads_rear,
    tire_front, tire_rear, fork, shock, brake_fluid, tubeless_sealant, bottom_bracket.
    If the bike doesn't exist yet, it will be created.
    """
    # Validate component type
    try:
        ComponentType(component_type)
    except ValueError:
        valid = ", ".join(ct.value for ct in ComponentType)
        return f"Invalid component type '{component_type}'. Valid types: {valid}"

    db: Database | None = None
    try:
        db, garage = await _get_garage()

        bike_id, created = await _get_or_create_bike(garage, bike_name)
        component = await garage.add_component(
            bike_id=bike_id,
            component_type=component_type,
            brand=brand,
            model=model,
        )

        brand_model = " ".join(filter(None, [brand, model])) or "unspecified"
        lines = []
        if created:
            lines.append(f"Created new bike: {bike_name}")
        lines.extend([
            f"Added {_format_component_type(component_type)} to {bike_name}",
            f"  Brand/Model: {brand_model}",
            f"  Installed: {component.installed_date.isoformat()}",
            f"  Component ID: {component.id}",
        ])

        # Show service interval info
        interval = SERVICE_INTERVALS.get(component_type)
        if interval is not None:
            interval_km, interval_hours, interval_months = interval
            if interval_km is not None:
                lines.append(f"  Service interval: {interval_km:.0f} effective km")
            if interval_hours is not None:
                lines.append(f"  Service interval: {interval_hours:.0f} hours")
            if interval_months is not None:
                lines.append(f"  Service interval: {interval_months} months")

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def bike_log_ride(
    bike_name: str,
    distance_km: float,
    duration_hours: float = 2.0,
    terrain: str = "S1",
    weather: str = "dry",
    avg_power_watts: float = 200.0,
    strava_activity_id: int | None = None,
) -> str:
    """Log a ride to update component wear.

    Automatically calculates effective km based on terrain, weather, and intensity.
    Optionally link to a Strava activity for auto-populated data.
    """
    db: Database | None = None
    try:
        db, garage = await _get_garage()

        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            return (
                f"Bike '{bike_name}' not found. "
                "Use bike_add_component to create a bike first."
            )

        effective = calculate_effective_km(
            actual_km=distance_km,
            terrain=terrain,
            weather=weather,
            avg_power_watts=avg_power_watts,
        )

        # Update bike total km
        await garage.update_bike_km(bike.id, distance_km)

        # Update all components
        components = await garage.get_components(bike.id)
        for comp in components:
            await garage.update_component_wear(comp.id, effective, duration_hours)

        lines = [
            f"Ride logged for {bike_name}",
            f"  Distance: {distance_km:.1f} km (actual)",
            f"  Effective km: {effective:.1f} km "
            f"(terrain: {terrain}, weather: {weather}, power: {avg_power_watts:.0f}W)",
            f"  Duration: {duration_hours:.1f}h",
        ]

        if strava_activity_id is not None:
            lines.append(f"  Strava activity: {strava_activity_id}")

        lines.append(f"  Components updated: {len(components)}")

        # Show wear status for components with warnings
        for comp in components:
            # Recalculate with updated values
            new_eff_km = comp.current_effective_km + effective
            new_hours = comp.current_hours + duration_hours
            status = get_wear_status(
                new_eff_km, new_hours, comp.installed_date, comp.type.value,
            )
            if status in ("warning", "critical", "overdue"):
                pct = calculate_wear_pct(
                    new_eff_km, new_hours, comp.installed_date, comp.type.value,
                )
                lines.append(
                    f"  ! {_format_component_type(comp.type.value)}: "
                    f"{pct:.0f}% worn ({status.upper()})"
                )

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def bike_maintenance_status(bike_name: str | None = None) -> str:
    """Check maintenance status for all components on a bike.

    Shows wear percentage, km remaining, and service urgency for each component.
    If no bike specified, shows status for all bikes.
    """
    db: Database | None = None
    try:
        db, garage = await _get_garage()

        if bike_name is not None:
            bike = await garage.get_bike_by_name(bike_name)
            if bike is None:
                return f"Bike '{bike_name}' not found."
            bikes = [bike]
        else:
            bikes = await garage.list_bikes()
            if not bikes:
                return (
                    "No bikes in the garage. "
                    "Use bike_add_component to add your first bike and component."
                )

        lines: list[str] = []
        for bike in bikes:
            lines.append(f"{'=' * 50}")
            lines.append(
                f"{bike.name} ({bike.bike_type.upper()}) - {bike.total_km:.0f} km total"
            )
            if bike.brand or bike.model:
                lines.append(
                    f"  {' '.join(filter(None, [bike.brand, bike.model]))}"
                )
            lines.append(f"{'=' * 50}")

            if not bike.components:
                lines.append("  No components tracked. Use bike_add_component to add some.")
                lines.append("")
                continue

            for comp in bike.components:
                pct = calculate_wear_pct(
                    comp.current_effective_km,
                    comp.current_hours,
                    comp.installed_date,
                    comp.type.value,
                )
                status = get_wear_status(
                    comp.current_effective_km,
                    comp.current_hours,
                    comp.installed_date,
                    comp.type.value,
                )
                remaining = km_remaining(comp.current_effective_km, comp.type.value)

                brand_model = " ".join(filter(None, [comp.brand, comp.model])) or "unspecified"

                # Status indicator
                if status == "overdue":
                    indicator = "[!!!]"
                elif status == "critical":
                    indicator = "[!! ]"
                elif status == "warning":
                    indicator = "[!  ]"
                else:
                    indicator = "[OK ]"

                lines.append(
                    f"  {indicator} {_format_component_type(comp.type.value)}: "
                    f"{pct:.0f}% worn - {status.upper()}"
                )
                lines.append(f"       Brand/Model: {brand_model}")
                lines.append(
                    f"       Effective km: {comp.current_effective_km:.0f} | "
                    f"Hours: {comp.current_hours:.1f} | "
                    f"Installed: {comp.installed_date.isoformat()}"
                )

                # Show relevant interval info
                interval = SERVICE_INTERVALS.get(comp.type.value)
                if interval is not None:
                    interval_km, interval_hours, interval_months = interval
                    if remaining is not None:
                        lines.append(f"       Remaining: {remaining:.0f} effective km")
                    if interval_hours is not None:
                        hrs_left = max(0.0, interval_hours - comp.current_hours)
                        lines.append(f"       Remaining: {hrs_left:.1f} hours")
                    if interval_months is not None:
                        lines.append(
                            f"       Service every {interval_months} months"
                        )

            lines.append("")

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def bike_service_log(
    bike_name: str,
    component_type: str,
    service_type: str = "replace",
    notes: str | None = None,
) -> str:
    """Log a maintenance service (replace, service, clean) for a component.

    Resets wear counter for the component. Service types: replace, service, clean.
    """
    # Validate component type
    try:
        ComponentType(component_type)
    except ValueError:
        valid = ", ".join(ct.value for ct in ComponentType)
        return f"Invalid component type '{component_type}'. Valid types: {valid}"

    valid_service_types = ("replace", "service", "clean")
    if service_type not in valid_service_types:
        return (
            f"Invalid service type '{service_type}'. "
            f"Valid types: {', '.join(valid_service_types)}"
        )

    db: Database | None = None
    try:
        db, garage = await _get_garage()

        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            return f"Bike '{bike_name}' not found."

        # Find the component on this bike
        matching = [c for c in bike.components if c.type.value == component_type]
        if not matching:
            return (
                f"No {_format_component_type(component_type)} found on {bike_name}. "
                "Use bike_add_component to add it first."
            )

        component = matching[0]

        # Log the service
        service = await garage.log_service(
            bike_id=bike.id,
            component_type=component_type,
            service_type=service_type,
            notes=notes,
        )

        # Reset the component wear counters
        await garage.reset_component(component.id)

        lines = [
            f"Service logged for {bike_name}",
            f"  Component: {_format_component_type(component_type)}",
            f"  Service type: {service_type}",
            f"  Date: {service.date.isoformat()}",
        ]

        if notes:
            lines.append(f"  Notes: {notes}")

        lines.extend([
            "",
            f"Wear counters reset for {_format_component_type(component_type)}.",
            f"  Previous effective km: {component.current_effective_km:.0f}",
            f"  Previous hours: {component.current_hours:.1f}",
        ])

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()
