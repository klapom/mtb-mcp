"""Bike garage storage -- CRUD operations for bikes, components, rides, and services.

Usage::

    async with Database(Path(":memory:")) as db:
        garage = BikeGarage(db)
        bike = await garage.add_bike("Trail Shredder", brand="Canyon", bike_type="mtb")
        await garage.add_component(bike.id, "chain", brand="Shimano", model="CN-M8100")
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

import structlog

from mtb_mcp.models.bike import Bike, Component, ComponentType, ServiceLog

if TYPE_CHECKING:
    from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)


class BikeGarage:
    """Manage bikes, components, and service history in SQLite."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # -----------------------------------------------------------------------
    # Bikes
    # -----------------------------------------------------------------------

    async def add_bike(
        self,
        name: str,
        brand: str | None = None,
        model: str | None = None,
        bike_type: str = "mtb",
        strava_gear_id: str | None = None,
    ) -> Bike:
        """Add a new bike to the garage.

        Args:
            name: Human-readable bike name (e.g. "Trail Shredder").
            brand: Bike manufacturer.
            model: Bike model name.
            bike_type: Type of bike (mtb, emtb, gravel, road).
            strava_gear_id: Optional Strava gear ID for linking.

        Returns:
            The newly created Bike.
        """
        bike_id = str(uuid.uuid4())
        await self._db.execute_and_commit(
            "INSERT INTO bikes (id, name, brand, model, bike_type, total_km, strava_gear_id) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (bike_id, name, brand, model, bike_type, strava_gear_id),
        )
        logger.info("bike_garage.bike_added", bike_id=bike_id, name=name)
        return Bike(
            id=bike_id,
            name=name,
            brand=brand,
            model=model,
            bike_type=bike_type,
            total_km=0.0,
            strava_gear_id=strava_gear_id,
        )

    async def get_bike(self, bike_id: str) -> Bike | None:
        """Get a bike by ID, including its components.

        Args:
            bike_id: The bike's UUID.

        Returns:
            The Bike with components, or None if not found.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM bikes WHERE id = ?", (bike_id,),
        )
        if row is None:
            return None

        components = await self.get_components(bike_id)
        return Bike(
            id=row["id"],
            name=row["name"],
            brand=row["brand"],
            model=row["model"],
            bike_type=row["bike_type"],
            total_km=row["total_km"],
            strava_gear_id=row["strava_gear_id"],
            components=components,
        )

    async def get_bike_by_name(self, name: str) -> Bike | None:
        """Get a bike by name (case-insensitive).

        Args:
            name: The bike name to search for.

        Returns:
            The Bike with components, or None if not found.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM bikes WHERE LOWER(name) = LOWER(?)", (name,),
        )
        if row is None:
            return None

        components = await self.get_components(row["id"])
        return Bike(
            id=row["id"],
            name=row["name"],
            brand=row["brand"],
            model=row["model"],
            bike_type=row["bike_type"],
            total_km=row["total_km"],
            strava_gear_id=row["strava_gear_id"],
            components=components,
        )

    async def list_bikes(self) -> list[Bike]:
        """List all bikes in the garage.

        Returns:
            A list of all bikes with their components.
        """
        rows = await self._db.fetch_all("SELECT * FROM bikes ORDER BY name")
        bikes: list[Bike] = []
        for row in rows:
            components = await self.get_components(row["id"])
            bikes.append(
                Bike(
                    id=row["id"],
                    name=row["name"],
                    brand=row["brand"],
                    model=row["model"],
                    bike_type=row["bike_type"],
                    total_km=row["total_km"],
                    strava_gear_id=row["strava_gear_id"],
                    components=components,
                )
            )
        return bikes

    async def update_bike_km(self, bike_id: str, km: float) -> None:
        """Add km to a bike's total distance.

        Args:
            bike_id: The bike's UUID.
            km: Kilometres to add.
        """
        await self._db.execute_and_commit(
            "UPDATE bikes SET total_km = total_km + ? WHERE id = ?",
            (km, bike_id),
        )

    # -----------------------------------------------------------------------
    # Components
    # -----------------------------------------------------------------------

    async def add_component(
        self,
        bike_id: str,
        component_type: str,
        brand: str | None = None,
        model: str | None = None,
        installed_date: date | None = None,
    ) -> Component:
        """Add a component to a bike for wear tracking.

        Args:
            bike_id: The bike's UUID.
            component_type: One of the ComponentType values.
            brand: Component manufacturer.
            model: Component model name.
            installed_date: Date installed (defaults to today).

        Returns:
            The newly created Component.
        """
        # Validate component type
        ComponentType(component_type)

        if installed_date is None:
            installed_date = date.today()

        component_id = str(uuid.uuid4())
        await self._db.execute_and_commit(
            "INSERT INTO components "
            "(id, bike_id, type, brand, model, installed_date, installed_km, "
            "current_effective_km, current_hours) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0)",
            (component_id, bike_id, component_type, brand, model,
             installed_date.isoformat()),
        )
        logger.info(
            "bike_garage.component_added",
            component_id=component_id,
            bike_id=bike_id,
            type=component_type,
        )
        return Component(
            id=component_id,
            type=ComponentType(component_type),
            brand=brand,
            model=model,
            installed_date=installed_date,
        )

    async def get_components(self, bike_id: str) -> list[Component]:
        """Get all components for a bike.

        Args:
            bike_id: The bike's UUID.

        Returns:
            List of components attached to the bike.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM components WHERE bike_id = ? ORDER BY type",
            (bike_id,),
        )
        return [
            Component(
                id=row["id"],
                type=ComponentType(row["type"]),
                brand=row["brand"],
                model=row["model"],
                installed_date=date.fromisoformat(row["installed_date"]),
                installed_km=row["installed_km"],
                current_effective_km=row["current_effective_km"],
                current_hours=row["current_hours"],
            )
            for row in rows
        ]

    async def update_component_wear(
        self, component_id: str, effective_km: float, hours: float,
    ) -> None:
        """Add effective km and hours to a component's wear counters.

        Args:
            component_id: The component's UUID.
            effective_km: Effective kilometres to add.
            hours: Riding hours to add.
        """
        await self._db.execute_and_commit(
            "UPDATE components "
            "SET current_effective_km = current_effective_km + ?, "
            "    current_hours = current_hours + ? "
            "WHERE id = ?",
            (effective_km, hours, component_id),
        )

    async def reset_component(self, component_id: str) -> None:
        """Reset a component's wear counters (after service/replacement).

        Also updates the installed_date to today.

        Args:
            component_id: The component's UUID.
        """
        today = date.today().isoformat()
        await self._db.execute_and_commit(
            "UPDATE components "
            "SET current_effective_km = 0, current_hours = 0, installed_date = ? "
            "WHERE id = ?",
            (today, component_id),
        )
        logger.info("bike_garage.component_reset", component_id=component_id)

    # -----------------------------------------------------------------------
    # Service Log
    # -----------------------------------------------------------------------

    async def log_service(
        self,
        bike_id: str,
        component_type: str,
        service_type: str,
        notes: str | None = None,
    ) -> ServiceLog:
        """Log a maintenance service event.

        Args:
            bike_id: The bike's UUID.
            component_type: Type of component serviced.
            service_type: Type of service (replace, service, clean).
            notes: Optional notes about the service.

        Returns:
            The newly created ServiceLog entry.
        """
        service_id = str(uuid.uuid4())
        today = date.today()
        await self._db.execute_and_commit(
            "INSERT INTO service_log (id, bike_id, component_type, service_type, date, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (service_id, bike_id, component_type, service_type,
             today.isoformat(), notes),
        )
        logger.info(
            "bike_garage.service_logged",
            service_id=service_id,
            bike_id=bike_id,
            component_type=component_type,
            service_type=service_type,
        )
        return ServiceLog(
            id=service_id,
            bike_id=bike_id,
            component_type=component_type,
            service_type=service_type,
            date=today,
            notes=notes,
        )

    async def get_service_history(
        self, bike_id: str, limit: int = 20,
    ) -> list[ServiceLog]:
        """Get service history for a bike, most recent first.

        Args:
            bike_id: The bike's UUID.
            limit: Maximum number of entries to return.

        Returns:
            List of service log entries.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM service_log WHERE bike_id = ? "
            "ORDER BY date DESC LIMIT ?",
            (bike_id, limit),
        )
        return [
            ServiceLog(
                id=row["id"],
                bike_id=row["bike_id"],
                component_type=row["component_type"],
                service_type=row["service_type"],
                date=date.fromisoformat(row["date"]),
                notes=row["notes"],
            )
            for row in rows
        ]
