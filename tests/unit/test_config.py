"""Tests for mtb_mcp.config."""

from pathlib import Path

import pytest

from mtb_mcp.config import Settings, get_settings


class TestSettings:
    """Test Settings model."""

    def test_default_values(self) -> None:
        """Settings should have sensible defaults."""
        s = Settings()
        assert s.log_level == "INFO"
        assert s.data_dir == Path("~/.mtb-mcp")
        assert s.db_path == Path("~/.mtb-mcp/mtb.db")
        assert s.home_lat == pytest.approx(49.59)
        assert s.home_lon == pytest.approx(11.00)
        assert s.default_radius_km == pytest.approx(30.0)

    def test_resolved_data_dir(self) -> None:
        """resolved_data_dir should expand ~."""
        s = Settings()
        resolved = s.resolved_data_dir
        assert "~" not in str(resolved)
        assert resolved.is_absolute()

    def test_resolved_db_path(self) -> None:
        """resolved_db_path should expand ~."""
        s = Settings()
        resolved = s.resolved_db_path
        assert "~" not in str(resolved)
        assert str(resolved).endswith("mtb.db")

    def test_optional_api_keys_default_none(self) -> None:
        """Optional API keys should default to None."""
        s = Settings()
        assert s.strava_client_id is None
        assert s.strava_client_secret is None
        assert s.komoot_email is None
        assert s.ors_api_key is None
        assert s.bosch_client_id is None
        assert s.wahoo_client_id is None

    def test_service_urls_have_defaults(self) -> None:
        """Service URLs should have sensible defaults."""
        s = Settings()
        assert s.brouter_url == "http://localhost:17777"
        assert s.searxng_url == "http://localhost:17888"
        assert "opendata.dwd.de" in s.dwd_base_url
        assert "overpass-api.de" in s.overpass_url

    def test_env_prefix(self) -> None:
        """Settings should use MTB_MCP_ prefix."""
        assert Settings.model_config["env_prefix"] == "MTB_MCP_"

    def test_override_via_constructor(self) -> None:
        """Settings should accept overrides."""
        s = Settings(log_level="DEBUG", home_lat=48.0, home_lon=10.0)
        assert s.log_level == "DEBUG"
        assert s.home_lat == pytest.approx(48.0)
        assert s.home_lon == pytest.approx(10.0)

    def test_get_settings_returns_instance(self) -> None:
        """get_settings() should return a Settings instance."""
        s = get_settings()
        assert isinstance(s, Settings)
