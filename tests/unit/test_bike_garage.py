"""Tests for the BikeGarage storage layer."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from mtb_mcp.models.bike import ComponentType
from mtb_mcp.storage.bike_garage import BikeGarage
from mtb_mcp.storage.database import Database


@pytest.fixture
async def garage() -> BikeGarage:
    """Create a BikeGarage with an in-memory database."""
    db = Database(Path(":memory:"))
    await db.initialize()
    garage = BikeGarage(db)
    yield garage  # type: ignore[misc]
    await db.close()


# ---------------------------------------------------------------------------
# Bike CRUD
# ---------------------------------------------------------------------------


class TestBikeCRUD:
    """Test add, get, list bikes."""

    async def test_add_bike(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Trail Shredder", brand="Canyon", model="Spectral")
        assert bike.name == "Trail Shredder"
        assert bike.brand == "Canyon"
        assert bike.model == "Spectral"
        assert bike.bike_type == "mtb"
        assert bike.total_km == 0.0
        assert bike.id  # should be a UUID string

    async def test_get_bike(self, garage: BikeGarage) -> None:
        added = await garage.add_bike("Enduro Machine")
        fetched = await garage.get_bike(added.id)
        assert fetched is not None
        assert fetched.name == "Enduro Machine"
        assert fetched.id == added.id

    async def test_get_bike_not_found(self, garage: BikeGarage) -> None:
        fetched = await garage.get_bike("nonexistent-id")
        assert fetched is None

    async def test_get_bike_by_name(self, garage: BikeGarage) -> None:
        await garage.add_bike("My Bike")
        fetched = await garage.get_bike_by_name("My Bike")
        assert fetched is not None
        assert fetched.name == "My Bike"

    async def test_get_bike_by_name_case_insensitive(self, garage: BikeGarage) -> None:
        await garage.add_bike("Trail Shredder")
        fetched = await garage.get_bike_by_name("trail shredder")
        assert fetched is not None
        assert fetched.name == "Trail Shredder"

    async def test_get_bike_by_name_not_found(self, garage: BikeGarage) -> None:
        fetched = await garage.get_bike_by_name("Nonexistent")
        assert fetched is None

    async def test_list_bikes_empty(self, garage: BikeGarage) -> None:
        bikes = await garage.list_bikes()
        assert bikes == []

    async def test_list_bikes_multiple(self, garage: BikeGarage) -> None:
        await garage.add_bike("Bike A")
        await garage.add_bike("Bike B")
        bikes = await garage.list_bikes()
        assert len(bikes) == 2
        names = {b.name for b in bikes}
        assert names == {"Bike A", "Bike B"}

    async def test_add_bike_with_strava_gear_id(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Strava Bike", strava_gear_id="g12345")
        assert bike.strava_gear_id == "g12345"

    async def test_update_bike_km(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("KM Tracker")
        await garage.update_bike_km(bike.id, 50.0)
        await garage.update_bike_km(bike.id, 30.0)
        fetched = await garage.get_bike(bike.id)
        assert fetched is not None
        assert fetched.total_km == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# Component CRUD
# ---------------------------------------------------------------------------


class TestComponentCRUD:
    """Test add, get components."""

    async def test_add_component(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Test Bike")
        comp = await garage.add_component(
            bike.id, "chain", brand="Shimano", model="CN-M8100",
        )
        assert comp.type == ComponentType.chain
        assert comp.brand == "Shimano"
        assert comp.model == "CN-M8100"
        assert comp.current_effective_km == 0.0
        assert comp.current_hours == 0.0

    async def test_add_component_default_date(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Test Bike")
        comp = await garage.add_component(bike.id, "chain")
        assert comp.installed_date == date.today()

    async def test_add_component_custom_date(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Test Bike")
        custom_date = date(2025, 3, 15)
        comp = await garage.add_component(
            bike.id, "chain", installed_date=custom_date,
        )
        assert comp.installed_date == custom_date

    async def test_add_invalid_component_type(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Test Bike")
        with pytest.raises(ValueError, match="invalid_type"):
            await garage.add_component(bike.id, "invalid_type")

    async def test_get_components(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Test Bike")
        await garage.add_component(bike.id, "chain")
        await garage.add_component(bike.id, "cassette")
        components = await garage.get_components(bike.id)
        assert len(components) == 2
        types = {c.type.value for c in components}
        assert types == {"chain", "cassette"}

    async def test_get_components_empty(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Empty Bike")
        components = await garage.get_components(bike.id)
        assert components == []

    async def test_bike_includes_components(self, garage: BikeGarage) -> None:
        """Getting a bike should include its components."""
        bike = await garage.add_bike("Full Bike")
        await garage.add_component(bike.id, "chain")
        await garage.add_component(bike.id, "fork")
        fetched = await garage.get_bike(bike.id)
        assert fetched is not None
        assert len(fetched.components) == 2


# ---------------------------------------------------------------------------
# Wear tracking
# ---------------------------------------------------------------------------


class TestWearTracking:
    """Test component wear updates and reset."""

    async def test_update_component_wear(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Wear Test")
        comp = await garage.add_component(bike.id, "chain")

        await garage.update_component_wear(comp.id, effective_km=50.0, hours=2.0)
        await garage.update_component_wear(comp.id, effective_km=30.0, hours=1.5)

        components = await garage.get_components(bike.id)
        assert len(components) == 1
        assert components[0].current_effective_km == pytest.approx(80.0)
        assert components[0].current_hours == pytest.approx(3.5)

    async def test_reset_component(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Reset Test")
        comp = await garage.add_component(
            bike.id, "chain", installed_date=date(2025, 1, 1),
        )
        await garage.update_component_wear(comp.id, effective_km=1000.0, hours=50.0)

        await garage.reset_component(comp.id)

        components = await garage.get_components(bike.id)
        assert len(components) == 1
        assert components[0].current_effective_km == 0.0
        assert components[0].current_hours == 0.0
        assert components[0].installed_date == date.today()


# ---------------------------------------------------------------------------
# Service log
# ---------------------------------------------------------------------------


class TestServiceLog:
    """Test service logging and history."""

    async def test_log_service(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Service Test")
        service = await garage.log_service(
            bike.id, "chain", "replace", notes="New Shimano chain",
        )
        assert service.bike_id == bike.id
        assert service.component_type == "chain"
        assert service.service_type == "replace"
        assert service.notes == "New Shimano chain"
        assert service.date == date.today()

    async def test_log_service_without_notes(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Service Test")
        service = await garage.log_service(bike.id, "brake_fluid", "replace")
        assert service.notes is None

    async def test_get_service_history(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("History Test")
        await garage.log_service(bike.id, "chain", "replace")
        await garage.log_service(bike.id, "chain", "clean", notes="Deep clean")
        await garage.log_service(bike.id, "brake_fluid", "replace")

        history = await garage.get_service_history(bike.id)
        assert len(history) == 3

    async def test_get_service_history_limit(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("Limit Test")
        for i in range(5):
            await garage.log_service(bike.id, "chain", "clean", notes=f"Clean {i}")

        history = await garage.get_service_history(bike.id, limit=3)
        assert len(history) == 3

    async def test_get_service_history_empty(self, garage: BikeGarage) -> None:
        bike = await garage.add_bike("No Service")
        history = await garage.get_service_history(bike.id)
        assert history == []
