# CLAUDE.md — TrailPilot MCP Server (mtb-mcp)

## Context Loss Recovery
1. [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md)
2. [docs/sprints/SPRINT_PLAN.md](docs/sprints/SPRINT_PLAN.md)
3. [docs/adr/ADR_INDEX.md](docs/adr/ADR_INDEX.md)
4. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
5. [docs/API_RESEARCH.md](docs/API_RESEARCH.md)

---

## Projekt-Übersicht

**mtb-mcp** = TrailPilot MCP Server — ein Python-basierter MCP-Server als "MTB Copilot"

| Komponente | Technologie | Zweck |
|-----------|------------|-------|
| MCP Server | FastMCP (Python) | Tool-Definitionen via @mcp.tool() |
| Transport | stdio | Via NanoClaw/mcporter |
| Wetter | DWD OpenData | Forecast, Regenradar, Alerts |
| Trails | OSM Overpass | MTB Trail-Katalog |
| Touren | Komoot + GPS-Tour.info | Multi-Source Tour-Suche |
| Tracking | Strava API v3 | Activities, Segments, GPX |
| Routing | BRouter (self-hosted) | MTB-optimierte Routen |
| Storage | SQLite (aiosqlite) | Bike Garage, Cache, History |
| Intelligence | Custom Algorithmen | Ride Score, Wear Engine, Trail Condition |

---

## Tech Stack

```yaml
Backend: Python 3.12+, Poetry, FastMCP
HTTP: httpx + tenacity (retry)
Models: Pydantic v2 + pydantic-settings
Storage: SQLite via aiosqlite (~/.mtb-mcp/mtb.db)
Logging: structlog
Docker: BRouter (17777) + SearXNG (17888)
Testing: pytest + respx (httpx mocking)
Quality: Ruff + MyPy (strict)
```

---

## Development Workflow

### Quick Commands
```bash
make dev          # Install + dev deps + pre-commit hooks
make run          # Start MCP server (stdio)
make test-unit    # Run unit tests
make lint         # Ruff check
make type-check   # MyPy strict
make quality      # lint + type-check
make docker-up    # Start BRouter + SearXNG
```

### Code Quality
- **1 Feature = 1 Commit** (Atomic Rollbacks)
- `make quality` before every commit
- Ruff line-length=100, select E/W/F/I/B/SIM
- MyPy strict mode

### MCP Tool Pattern
```python
from mtb_mcp.server import mcp

@mcp.tool()
def tool_name(param: str) -> str:
    """Tool description for MCP clients."""
    return "result"
```

### API Client Pattern
```python
from mtb_mcp.clients.base import BaseClient

class MyClient(BaseClient):
    async def fetch_data(self) -> dict:
        return await self._get("/endpoint")
```

---

## mcporter Registration

```json
// /home/admin/projects/nanoclaw/config/mcporter.json
{
  "mtb": {
    "command": "/home/admin/projects/mtb-mcp/.venv/bin/python -m mtb_mcp.cli"
  }
}
```

---

## Environment Variables

```bash
MTB_MCP_LOG_LEVEL=INFO
MTB_MCP_HOME_LAT=49.59      # Default search center
MTB_MCP_HOME_LON=11.00
MTB_MCP_STRAVA_CLIENT_ID=    # Strava OAuth
MTB_MCP_KOMOOT_EMAIL=        # Komoot Basic Auth
MTB_MCP_ORS_API_KEY=         # OpenRouteService
MTB_MCP_BROUTER_URL=http://localhost:17777
MTB_MCP_SEARXNG_URL=http://localhost:17888
```

See `.env.template` for all variables.

---

## Key ADRs

| ADR | Entscheidung |
|-----|-------------|
| ADR-001 | Python statt TypeScript (BLE, kompy, AEGISRAG-Ökosystem) |
| ADR-002 | FastMCP statt Low-Level Server |
| ADR-003 | SQLite für lokale Daten |
| ADR-004 | Self-Hosted BRouter für MTB-Routing |
| ADR-005 | DWD statt OpenWeatherMap |
| ADR-006 | kompy Wrapper für Komoot |

---

## MCP Tool Domains (38 Tools geplant)

| Domain | Tools | Sprint |
|--------|-------|--------|
| Strava | 7 | Sprint 5 |
| Tour-Suche | 6 | Sprint 4 |
| Trail-Info | 3 | Sprint 3 |
| Wetter | 4 | Sprint 3 |
| Routing | 3 | Sprint 6 |
| Intelligence | 5 | Sprint 7-8 |
| Bike Maintenance | 4 | Sprint 9-10 |
| BLE Sensoren | 2 | Sprint 11 |
| eBike | 2 | Sprint 12 |
| Safety | 2 | Sprint 14 |
