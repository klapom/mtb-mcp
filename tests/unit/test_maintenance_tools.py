"""Tests for maintenance MCP tools."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from mtb_mcp.storage.bike_garage import BikeGarage
from mtb_mcp.storage.database import Database
from mtb_mcp.tools.maintenance_tools import (
    bike_add_component,
    bike_log_ride,
    bike_maintenance_status,
    bike_service_log,
)


@pytest.fixture
def mock_garage_setup() -> tuple[AsyncMock, AsyncMock]:
    """Create mock Database and BikeGarage for tool tests.

    Returns:
        Tuple of (mock_db, mock_garage_fn) for patching _get_garage.
    """
    mock_db = AsyncMock(spec=Database)
    mock_garage = AsyncMock(spec=BikeGarage)
    return mock_db, mock_garage


def _patch_get_garage(mock_db: AsyncMock, mock_garage: AsyncMock) -> AsyncMock:
    """Create a patched _get_garage that returns mocks."""
    async def _fake_get_garage() -> tuple[AsyncMock, AsyncMock]:
        return mock_db, mock_garage
    return _fake_get_garage


# ---------------------------------------------------------------------------
# bike_add_component
# ---------------------------------------------------------------------------


class TestBikeAddComponent:
    """Tests for the bike_add_component tool."""

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_add_component_to_existing_bike(
        self, mock_get_garage: AsyncMock,
    ) -> None:
        """Adding a component to an existing bike."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        # Simulate existing bike
        from mtb_mcp.models.bike import Bike, Component, ComponentType

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="Trail Shredder", bike_type="mtb",
        )
        mock_garage.add_component.return_value = Component(
            id="comp-1", type=ComponentType.chain,
            brand="Shimano", model="CN-M8100",
            installed_date=date(2025, 6, 1),
        )

        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_add_component(
            bike_name="Trail Shredder",
            component_type="chain",
            brand="Shimano",
            model="CN-M8100",
        )

        assert "Chain" in result
        assert "Trail Shredder" in result
        assert "Shimano CN-M8100" in result
        assert "1500" in result  # service interval
        mock_garage.add_component.assert_called_once()

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_auto_create_bike(self, mock_get_garage: AsyncMock) -> None:
        """Bike should be auto-created if it doesn't exist."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike, Component, ComponentType

        mock_garage.get_bike_by_name.return_value = None
        mock_garage.add_bike.return_value = Bike(
            id="new-bike", name="New Bike", bike_type="mtb",
        )
        mock_garage.add_component.return_value = Component(
            id="comp-1", type=ComponentType.chain,
            installed_date=date(2025, 6, 1),
        )

        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_add_component(
            bike_name="New Bike",
            component_type="chain",
        )

        assert "Created new bike: New Bike" in result
        mock_garage.add_bike.assert_called_once_with("New Bike")

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_invalid_component_type(self, mock_get_garage: AsyncMock) -> None:
        """Invalid component type should return error message."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_add_component(
            bike_name="Test", component_type="invalid_type",
        )

        assert "Invalid component type" in result
        assert "chain" in result  # should list valid types


# ---------------------------------------------------------------------------
# bike_log_ride
# ---------------------------------------------------------------------------


class TestBikeLogRide:
    """Tests for the bike_log_ride tool."""

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_ride_basic(self, mock_get_garage: AsyncMock) -> None:
        """Basic ride logging should update all components."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike, Component, ComponentType

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="Test Bike", bike_type="mtb",
        )
        mock_garage.get_components.return_value = [
            Component(
                id="c1", type=ComponentType.chain,
                installed_date=date(2025, 1, 1),
                current_effective_km=0.0, current_hours=0.0,
            ),
            Component(
                id="c2", type=ComponentType.cassette,
                installed_date=date(2025, 1, 1),
                current_effective_km=0.0, current_hours=0.0,
            ),
        ]

        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_log_ride(
            bike_name="Test Bike",
            distance_km=30.0,
            duration_hours=2.0,
        )

        assert "Ride logged" in result
        assert "30.0 km" in result
        assert "Components updated: 2" in result
        mock_garage.update_bike_km.assert_called_once_with("bike-1", 30.0)
        assert mock_garage.update_component_wear.call_count == 2

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_ride_bike_not_found(self, mock_get_garage: AsyncMock) -> None:
        """Logging a ride for nonexistent bike should return error."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_garage.get_bike_by_name.return_value = None
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_log_ride(bike_name="Ghost Bike", distance_km=10.0)

        assert "not found" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_ride_effective_km_display(self, mock_get_garage: AsyncMock) -> None:
        """Ride log should show effective km with modifiers."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="MTB", bike_type="mtb",
        )
        mock_garage.get_components.return_value = []
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_log_ride(
            bike_name="MTB",
            distance_km=20.0,
            terrain="S3",
            weather="wet",
            avg_power_watts=300.0,
        )

        assert "Effective km:" in result
        assert "S3" in result
        assert "wet" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_ride_strava_activity(self, mock_get_garage: AsyncMock) -> None:
        """Strava activity ID should be included in output."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="MTB", bike_type="mtb",
        )
        mock_garage.get_components.return_value = []
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_log_ride(
            bike_name="MTB", distance_km=10.0, strava_activity_id=12345,
        )

        assert "12345" in result


# ---------------------------------------------------------------------------
# bike_maintenance_status
# ---------------------------------------------------------------------------


class TestBikeMaintenanceStatus:
    """Tests for the bike_maintenance_status tool."""

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_status_single_bike(self, mock_get_garage: AsyncMock) -> None:
        """Should show status for a specific bike."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike, Component, ComponentType

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="Test Bike", bike_type="mtb",
            total_km=500.0,
            components=[
                Component(
                    id="c1", type=ComponentType.chain,
                    brand="Shimano", model="CN-M8100",
                    installed_date=date(2025, 1, 1),
                    current_effective_km=900.0, current_hours=30.0,
                ),
            ],
        )
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_maintenance_status(bike_name="Test Bike")

        assert "Test Bike" in result
        assert "Chain" in result
        assert "Shimano CN-M8100" in result
        assert "%" in result  # wear percentage

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_status_all_bikes(self, mock_get_garage: AsyncMock) -> None:
        """Should show status for all bikes when no name given."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike

        mock_garage.list_bikes.return_value = [
            Bike(id="b1", name="Bike A", bike_type="mtb", components=[]),
            Bike(id="b2", name="Bike B", bike_type="gravel", components=[]),
        ]
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_maintenance_status()

        assert "Bike A" in result
        assert "Bike B" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_status_no_bikes(self, mock_get_garage: AsyncMock) -> None:
        """Should return helpful message when no bikes exist."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_garage.list_bikes.return_value = []
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_maintenance_status()

        assert "No bikes" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_status_bike_not_found(self, mock_get_garage: AsyncMock) -> None:
        """Should return error when specified bike not found."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_garage.get_bike_by_name.return_value = None
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_maintenance_status(bike_name="Ghost")

        assert "not found" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_status_shows_wear_indicators(self, mock_get_garage: AsyncMock) -> None:
        """Status should show [OK], [!], [!!], [!!!] indicators."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike, Component, ComponentType

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="Test", bike_type="mtb",
            components=[
                Component(
                    id="c1", type=ComponentType.chain,
                    installed_date=date(2025, 1, 1),
                    current_effective_km=100.0, current_hours=5.0,
                ),
                Component(
                    id="c2", type=ComponentType.cassette,
                    installed_date=date(2025, 1, 1),
                    current_effective_km=3500.0, current_hours=150.0,
                ),
            ],
        )
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_maintenance_status(bike_name="Test")

        assert "[OK ]" in result  # chain at ~7%
        assert "[!! ]" in result or "[!!!]" in result  # cassette at ~87%


# ---------------------------------------------------------------------------
# bike_service_log
# ---------------------------------------------------------------------------


class TestBikeServiceLog:
    """Tests for the bike_service_log tool."""

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_service_replace(self, mock_get_garage: AsyncMock) -> None:
        """Logging a replace service should reset wear counters."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike, Component, ComponentType, ServiceLog

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="Test Bike", bike_type="mtb",
            components=[
                Component(
                    id="c1", type=ComponentType.chain,
                    brand="Shimano",
                    installed_date=date(2025, 1, 1),
                    current_effective_km=1600.0, current_hours=80.0,
                ),
            ],
        )
        mock_garage.log_service.return_value = ServiceLog(
            id="svc-1", bike_id="bike-1",
            component_type="chain", service_type="replace",
            date=date.today(),
        )
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_service_log(
            bike_name="Test Bike",
            component_type="chain",
            service_type="replace",
            notes="New chain installed",
        )

        assert "Service logged" in result
        assert "Chain" in result
        assert "replace" in result
        assert "Wear counters reset" in result
        mock_garage.reset_component.assert_called_once_with("c1")

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_service_invalid_component(self, mock_get_garage: AsyncMock) -> None:
        """Invalid component type should return error."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_service_log(
            bike_name="Test", component_type="invalid_type",
        )

        assert "Invalid component type" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_service_invalid_service_type(self, mock_get_garage: AsyncMock) -> None:
        """Invalid service type should return error."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_service_log(
            bike_name="Test", component_type="chain", service_type="invalid",
        )

        assert "Invalid service type" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_service_bike_not_found(self, mock_get_garage: AsyncMock) -> None:
        """Service log for nonexistent bike should return error."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)
        mock_garage.get_bike_by_name.return_value = None
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_service_log(
            bike_name="Ghost", component_type="chain",
        )

        assert "not found" in result

    @patch("mtb_mcp.tools.maintenance_tools._get_garage")
    async def test_log_service_component_not_on_bike(
        self, mock_get_garage: AsyncMock,
    ) -> None:
        """Service log for a component not on the bike should return error."""
        mock_db = AsyncMock()
        mock_garage = AsyncMock(spec=BikeGarage)

        from mtb_mcp.models.bike import Bike

        mock_garage.get_bike_by_name.return_value = Bike(
            id="bike-1", name="Test", bike_type="mtb", components=[],
        )
        mock_get_garage.return_value = (mock_db, mock_garage)

        result = await bike_service_log(
            bike_name="Test", component_type="chain",
        )

        assert "No" in result
        assert "Chain" in result
