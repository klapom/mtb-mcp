"""Bike garage endpoints — CRUD, wear tracking, service log."""
from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from mtb_mcp.api.deps import get_cached_settings
from mtb_mcp.api.models import err, ok, ok_list
from mtb_mcp.intelligence.wear_engine import (
    SERVICE_INTERVALS,
    calculate_effective_km,
    calculate_wear_pct,
    get_wear_status,
    km_remaining,
)
from mtb_mcp.models.bike import ComponentType
from mtb_mcp.storage.bike_garage import BikeGarage
from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class AddComponentRequest(BaseModel):
    component_type: str
    brand: str | None = None
    model: str | None = None


class LogRideRequest(BaseModel):
    distance_km: float
    duration_hours: float = 2.0
    terrain: str = "S1"
    weather: str = "dry"
    avg_power_watts: float = 200.0
    strava_activity_id: int | None = None


class ServiceRequest(BaseModel):
    component_type: str
    service_type: str = "replace"
    notes: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _open_garage() -> tuple[Database, BikeGarage]:
    """Open a Database and BikeGarage from cached settings."""
    settings = get_cached_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db, BikeGarage(db)


def _bike_to_dict(bike: Any) -> dict[str, Any]:
    """Serialize a Bike model to a dict with wear info on every component."""
    components = []
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

        interval = SERVICE_INTERVALS.get(comp.type.value)
        interval_km = interval[0] if interval else None
        interval_hours = interval[1] if interval else None
        interval_months = interval[2] if interval else None

        components.append({
            "id": comp.id,
            "type": comp.type.value,
            "brand": comp.brand,
            "model": comp.model,
            "installed_date": comp.installed_date.isoformat(),
            "current_effective_km": comp.current_effective_km,
            "current_hours": comp.current_hours,
            "wear_pct": round(pct, 1),
            "status": status,
            "km_remaining": round(remaining, 0) if remaining is not None else None,
            "service_interval_km": interval_km,
            "service_interval_hours": interval_hours,
            "service_interval_months": interval_months,
        })

    return {
        "id": bike.id,
        "name": bike.name,
        "brand": bike.brand,
        "model": bike.model,
        "bike_type": bike.bike_type,
        "total_km": bike.total_km,
        "strava_gear_id": bike.strava_gear_id,
        "components": components,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", include_in_schema=False)
@router.get("/")
async def list_bikes() -> dict[str, Any]:
    """List all bikes with components and wear status."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, garage = await _open_garage()
        bikes = await garage.list_bikes()
        items = [_bike_to_dict(b) for b in bikes]
        return ok_list(items, total=len(items), start_time=t)
    except Exception as exc:
        logger.error("list_bikes_error", error=str(exc))
        return err("DB_ERROR", f"Failed to list bikes: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/{bike_name}")
async def get_bike(bike_name: str) -> dict[str, Any]:
    """Get a single bike with all components and wear details."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, garage = await _open_garage()
        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            return err("NOT_FOUND", f"Bike '{bike_name}' not found")
        return ok(_bike_to_dict(bike), t)
    except Exception as exc:
        logger.error("get_bike_error", error=str(exc))
        return err("DB_ERROR", f"Failed to get bike: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/{bike_name}/components")
async def add_component(bike_name: str, body: AddComponentRequest) -> dict[str, Any]:
    """Add a component to a bike for wear tracking."""
    t = time.monotonic()

    # Validate component type early
    try:
        ComponentType(body.component_type)
    except ValueError:
        valid = ", ".join(ct.value for ct in ComponentType)
        return err("INVALID_COMPONENT_TYPE", f"Invalid type '{body.component_type}'. Valid: {valid}")

    db: Database | None = None
    try:
        db, garage = await _open_garage()

        # Find bike; create if not found
        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            bike = await garage.add_bike(bike_name)

        component = await garage.add_component(
            bike_id=bike.id,
            component_type=body.component_type,
            brand=body.brand,
            model=body.model,
        )

        return ok(
            {
                "component_id": component.id,
                "bike_id": bike.id,
                "bike_name": bike.name,
                "type": component.type.value,
                "brand": component.brand,
                "model": component.model,
                "installed_date": component.installed_date.isoformat(),
            },
            t,
        )
    except Exception as exc:
        logger.error("add_component_error", error=str(exc))
        return err("DB_ERROR", f"Failed to add component: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/{bike_name}/rides")
async def log_ride(bike_name: str, body: LogRideRequest) -> dict[str, Any]:
    """Log a ride — updates bike km and all component wear counters."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, garage = await _open_garage()

        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            return err("NOT_FOUND", f"Bike '{bike_name}' not found")

        effective = calculate_effective_km(
            actual_km=body.distance_km,
            terrain=body.terrain,
            weather=body.weather,
            avg_power_watts=body.avg_power_watts,
        )

        # Update bike total km
        await garage.update_bike_km(bike.id, body.distance_km)

        # Update all components
        components = await garage.get_components(bike.id)
        for comp in components:
            await garage.update_component_wear(comp.id, effective, body.duration_hours)

        # Build wear warnings for response
        warnings: list[dict[str, Any]] = []
        for comp in components:
            new_eff = comp.current_effective_km + effective
            new_hrs = comp.current_hours + body.duration_hours
            status = get_wear_status(
                new_eff, new_hrs, comp.installed_date, comp.type.value,
            )
            if status in ("warning", "critical", "overdue"):
                pct = calculate_wear_pct(
                    new_eff, new_hrs, comp.installed_date, comp.type.value,
                )
                warnings.append({
                    "component_type": comp.type.value,
                    "wear_pct": round(pct, 1),
                    "status": status,
                })

        return ok(
            {
                "bike_name": bike.name,
                "distance_km": body.distance_km,
                "effective_km": round(effective, 1),
                "duration_hours": body.duration_hours,
                "terrain": body.terrain,
                "weather": body.weather,
                "avg_power_watts": body.avg_power_watts,
                "strava_activity_id": body.strava_activity_id,
                "components_updated": len(components),
                "warnings": warnings,
            },
            t,
        )
    except Exception as exc:
        logger.error("log_ride_error", error=str(exc))
        return err("DB_ERROR", f"Failed to log ride: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/{bike_name}/maintenance")
async def maintenance_status(bike_name: str) -> dict[str, Any]:
    """Maintenance status for all components — wear %, status, km remaining."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, garage = await _open_garage()

        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            return err("NOT_FOUND", f"Bike '{bike_name}' not found")

        components: list[dict[str, Any]] = []
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

            interval = SERVICE_INTERVALS.get(comp.type.value)
            interval_km = interval[0] if interval else None
            interval_hours = interval[1] if interval else None
            interval_months = interval[2] if interval else None

            components.append({
                "component_type": comp.type.value,
                "brand": comp.brand,
                "model": comp.model,
                "wear_pct": round(pct, 1),
                "status": status,
                "effective_km": comp.current_effective_km,
                "hours": comp.current_hours,
                "installed_date": comp.installed_date.isoformat(),
                "km_remaining": round(remaining, 0) if remaining is not None else None,
                "service_interval_km": interval_km,
                "service_interval_hours": interval_hours,
                "service_interval_months": interval_months,
            })

        return ok(
            {
                "bike_name": bike.name,
                "bike_type": bike.bike_type,
                "total_km": bike.total_km,
                "components": components,
            },
            t,
        )
    except Exception as exc:
        logger.error("maintenance_status_error", error=str(exc))
        return err("DB_ERROR", f"Failed to get maintenance status: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/{bike_name}/service")
async def log_service(bike_name: str, body: ServiceRequest) -> dict[str, Any]:
    """Log a maintenance service — resets wear counters for the component."""
    t = time.monotonic()

    # Validate component type
    try:
        ComponentType(body.component_type)
    except ValueError:
        valid = ", ".join(ct.value for ct in ComponentType)
        return err("INVALID_COMPONENT_TYPE", f"Invalid type '{body.component_type}'. Valid: {valid}")

    valid_service_types = ("replace", "service", "clean")
    if body.service_type not in valid_service_types:
        return err(
            "INVALID_SERVICE_TYPE",
            f"Invalid service type '{body.service_type}'. "
            f"Valid: {', '.join(valid_service_types)}",
        )

    db: Database | None = None
    try:
        db, garage = await _open_garage()

        bike = await garage.get_bike_by_name(bike_name)
        if bike is None:
            return err("NOT_FOUND", f"Bike '{bike_name}' not found")

        # Find the component on this bike
        matching = [c for c in bike.components if c.type.value == body.component_type]
        if not matching:
            return err(
                "COMPONENT_NOT_FOUND",
                f"No {body.component_type} found on {bike_name}",
            )

        component = matching[0]
        prev_km = component.current_effective_km
        prev_hours = component.current_hours

        # Log the service
        service = await garage.log_service(
            bike_id=bike.id,
            component_type=body.component_type,
            service_type=body.service_type,
            notes=body.notes,
        )

        # Reset wear counters
        await garage.reset_component(component.id)

        return ok(
            {
                "service_id": service.id,
                "bike_name": bike.name,
                "component_type": body.component_type,
                "service_type": body.service_type,
                "date": service.date.isoformat(),
                "notes": body.notes,
                "previous_effective_km": round(prev_km, 1),
                "previous_hours": round(prev_hours, 1),
                "counters_reset": True,
            },
            t,
        )
    except Exception as exc:
        logger.error("log_service_error", error=str(exc))
        return err("DB_ERROR", f"Failed to log service: {exc}")
    finally:
        if db is not None:
            await db.close()
