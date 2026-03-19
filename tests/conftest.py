"""Shared test fixtures for mtb-mcp."""

import pytest

from mtb_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Return a Settings instance with test defaults."""
    return Settings(
        log_level="DEBUG",
        data_dir="./test-data",
        db_path="./test-data/test.db",
        home_lat=49.59,
        home_lon=11.00,
    )
