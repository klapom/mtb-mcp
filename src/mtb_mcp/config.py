"""MTB MCP Server configuration via environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the MTB MCP Server.

    All settings can be overridden via environment variables with the MTB_MCP_ prefix.
    Example: MTB_MCP_LOG_LEVEL=DEBUG
    """

    # General
    log_level: str = "INFO"
    data_dir: Path = Field(default=Path("~/.mtb-mcp"))
    db_path: Path = Field(default=Path("~/.mtb-mcp/mtb.db"))

    # Home location (default: Erlangen area)
    home_lat: float = 49.59
    home_lon: float = 11.00
    default_radius_km: float = 30.0

    # Auth
    jwt_secret: str = ""
    token_encryption_key: str = ""
    strava_oauth_redirect_uri: str = "http://localhost:3000/auth/callback"

    # Strava API
    strava_client_id: str | None = None
    strava_client_secret: str | None = None
    strava_access_token: str | None = None
    strava_refresh_token: str | None = None

    # Komoot
    komoot_email: str | None = None
    komoot_password: str | None = None

    # GPS-Tour.info
    gpstour_username: str | None = None
    gpstour_password: str | None = None

    # OpenRouteService
    ors_api_key: str | None = None

    # BRouter
    brouter_url: str = "http://localhost:17777"

    # SearXNG
    searxng_url: str = "http://localhost:17888"

    # DWD (no auth needed)
    dwd_base_url: str = "https://opendata.dwd.de"

    # Overpass (no auth needed)
    overpass_url: str = "https://overpass-api.de/api/interpreter"

    # Bosch eBike (future)
    bosch_client_id: str | None = None
    bosch_client_secret: str | None = None

    # Wahoo (future)
    wahoo_client_id: str | None = None
    wahoo_client_secret: str | None = None

    model_config = {
        "env_prefix": "MTB_MCP_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def resolved_data_dir(self) -> Path:
        """Return the data directory with ~ expanded."""
        return self.data_dir.expanduser()

    @property
    def resolved_db_path(self) -> Path:
        """Return the database path with ~ expanded."""
        return self.db_path.expanduser()


def get_settings() -> Settings:
    """Create and return a Settings instance."""
    return Settings()
