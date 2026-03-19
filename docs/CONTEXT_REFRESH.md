# Context Refresh — mtb-mcp

Quick recovery guide when context is lost.

## Was ist mtb-mcp?

Ein Python-basierter MCP-Server ("TrailPilot") der als MTB Copilot fungiert. Orchestriert externe APIs (Strava, Komoot, DWD, OSM), BLE-Sensordaten und intelligente Algorithmen. Läuft via NanoClaw/mcporter (stdio Transport).

## Architektur

```
User → mcporter → mtb-mcp (stdio) → FastMCP Server
                                    ├── tools/       (38 MCP Tools, 10 Domains)
                                    ├── clients/     (API Clients: httpx + retry)
                                    ├── intelligence/ (Ride Score, Wear Engine, Trail Condition)
                                    ├── storage/     (SQLite: Bike Garage, Cache)
                                    └── ble/         (BLE: TyreWiz, HR, Power)
```

## Kern-Entscheidungen

- **Python** wegen BLE (bleak), kompy, AEGISRAG-Ökosystem
- **FastMCP** via `@mcp.tool()` Decorator, `mcp.run(transport="stdio")`
- **SQLite** unter `~/.mtb-mcp/mtb.db` für lokale Daten
- **DWD** statt OpenWeatherMap (kostenlos, DACH-Fokus)
- **BRouter** self-hosted für echtes MTB-Routing

## Wo finde ich was?

| Info | Datei |
|------|-------|
| Sprint-Stand | `docs/sprints/SPRINT_PLAN.md` |
| API-Recherche | `docs/API_RESEARCH.md` |
| Use Cases | `docs/USE_CASES.md` |
| ADRs | `docs/adr/ADR_INDEX.md` |
| Architektur | `docs/ARCHITECTURE.md` |
| Config | `src/mtb_mcp/config.py` |
| Server | `src/mtb_mcp/server.py` |
