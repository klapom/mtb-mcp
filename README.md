# TrailPilot MCP Server (mtb-mcp)

> Your AI-powered MTB Copilot — weather-aware ride planning, trail conditions, bike maintenance, and more.

## What is this?

A Python-based MCP (Model Context Protocol) server that acts as a comprehensive mountain biking assistant. Connects to Strava, Komoot, DWD Weather, OpenStreetMap, and more to provide intelligent riding recommendations.

## Features

- **38 MCP Tools** across 11 domains
- **Multi-Source Tour Search** — Komoot + GPS-Tour.info with deduplication
- **Weather-Aware** — DWD forecasts, rain radar, trail condition estimation
- **Ride Score** — "Should I ride today?" (0-100) combining weather, trails, wind, daylight
- **Bike Maintenance** — Component wear tracking with terrain/weather modifiers
- **eBike Range** — Battery vs. elevation profile calculator
- **Weekend Planner** — Proactive Saturday/Sunday ride recommendations
- **Safety Timer** — Expected return time tracking
- **Fitness Tracking** — CTL/ATL/TSB, training plans, race readiness
- **BLE Sensors** — TyreWiz pressure, heart rate (optional)

## Quick Start

```bash
# Install
poetry install --with dev

# Run
python -m mtb_mcp

# Or via mcporter
# Add to nanoclaw/config/mcporter.json
```

## Tool Domains

| Domain | Tools | Description |
|--------|-------|-------------|
| Strava | 7 | Activities, segments, GPX export |
| Tour Search | 6 | Unified Komoot + GPS-Tour.info search |
| Trail Info | 3 | OSM trail data, conditions |
| Weather | 4 | DWD forecast, rain radar, alerts |
| Routing | 3 | BRouter/ORS MTB routing |
| Intelligence | 5 | Ride score, fusion, trail tagger |
| Maintenance | 4 | Bike wear tracking |
| Sensors | 2 | BLE heart rate, tire pressure |
| eBike | 2 | Range calculator |
| Safety | 2 | Return timer |
| Fitness | 7 | CTL/ATL/TSB, training plans |

## Configuration

Copy `.env.template` to `.env` and fill in your API credentials.

## Development

```bash
make dev          # Install + dev deps
make test-unit    # Run tests
make lint         # Ruff check
make type-check   # MyPy strict
make quality      # All checks
make docker-up    # Start BRouter + SearXNG
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## License

MIT
