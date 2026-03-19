# Architecture — TrailPilot MCP Server

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Claude / MCP Client                        │
└──────────────────────┬───────────────────────────────────────┘
                       │ stdio (MCP Protocol)
                       │
┌──────────────────────▼───────────────────────────────────────┐
│                 mcporter (NanoClaw)                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              mtb-mcp FastMCP Server                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    tools/ (38 Tools)                     │ │
│  │  strava · tour_search · trail · weather · routing       │ │
│  │  intelligence · maintenance · sensor · ebike · safety   │ │
│  └────────────────────────┬────────────────────────────────┘ │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │                  intelligence/                          │ │
│  │  ride_score · wear_engine · trail_condition             │ │
│  │  tour_fusion · trail_tagger · ebike_range               │ │
│  │  weekend_planner                                        │ │
│  └────────────────────────┬────────────────────────────────┘ │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │                   clients/                              │ │
│  │  strava · komoot · overpass · dwd · brouter · ors       │ │
│  │  gpstour · trailforks · mtbproject · bosch · wahoo      │ │
│  └────────────────────────┬────────────────────────────────┘ │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │              storage/ + ble/ + utils/                   │ │
│  │  SQLite · Cache · Bike Garage · BLE Scanner · Geo/GPX  │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         │              │              │            │
    ┌────▼───┐    ┌─────▼────┐   ┌────▼───┐  ┌────▼────┐
    │ Strava │    │  Komoot  │   │  DWD   │  │ BRouter │
    │ API v3 │    │ v007 API │   │OpenData│  │ Docker  │
    └────────┘    └──────────┘   └────────┘  └─────────┘
```

## Layers

### 1. Tools Layer (`tools/`)
MCP tool definitions via `@mcp.tool()` decorator. Each tool:
- Validates input (Pydantic models)
- Calls clients/intelligence
- Returns formatted string for MCP response

### 2. Intelligence Layer (`intelligence/`)
Smart algorithms that combine data from multiple sources:
- **Ride Score:** Weather + Trail + Wind + Daylight → Score 0-100
- **Wear Engine:** Effective-km with terrain/weather/intensity modifiers
- **Trail Condition:** Rain history + surface type → estimated condition
- **Tour Fusion:** Multi-source deduplication and enrichment
- **Trail Tagger:** GPS trace → known trail name matching

### 3. Clients Layer (`clients/`)
External API clients, all inheriting from `BaseClient`:
- httpx async HTTP
- tenacity retry with exponential backoff
- Token-bucket rate limiting per API
- Response caching

### 4. Foundation Layer (`storage/`, `ble/`, `utils/`)
- **SQLite:** Bike garage, API cache, tour history
- **BLE:** bleak-based sensor discovery and data reading
- **Utils:** Haversine, GPX parsing, unit conversion

## Data Flow Examples

### "Soll ich heute fahren?"
```
ride_score tool → DWD client (forecast)
               → Overpass client (trails near home)
               → intelligence/trail_condition (rain + surface)
               → intelligence/ride_score (combine all → score 0-100)
```

### "Finde MTB-Touren bei Erlangen"
```
search_tours tool → Komoot client (search)
                  → GPS-Tour client (SearXNG + scrape)
                  → intelligence/tour_fusion (deduplicate + merge)
```

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| BRouter | 17777 | MTB-optimized routing |
| SearXNG | 17888 | Meta-search for GPS-Tour.info |
