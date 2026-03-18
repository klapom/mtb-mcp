# MTB MCP Server

MCP server for mountainbike & outdoor activities — integrates Strava, Komoot, trail databases, and weather-aware ride planning. Built for [NanoClaw](https://github.com/qwibitai/nanoclaw).

## Use Cases

See [docs/USE_CASES.md](docs/USE_CASES.md) for the full use case catalog.

**Highlights:**
- "Zeig mir meine letzten MTB-Fahrten" → Strava activity history
- "Finde eine MTB-Tour bei Erlangen, 30-50km" → Komoot tour search
- "Kann ich morgen biken?" → Weather + trail conditions check
- "Wie sind die Trails am Hetzlas?" → OSM trail data + weather overlay
- Proaktiver Samstag-Morgen-Bericht: Wetter + Tour-Empfehlung

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  NanoClaw   │────▶│   mtb-mcp    │────▶│  External APIs   │
│  (mcporter) │     │  MCP Server  │     │                   │
└─────────────┘     └──────────────┘     │ • Strava API v3   │
                                          │ • Komoot v007     │
                                          │ • OSM Overpass    │
                                          │ • OpenRouteService│
                                          │ • Weather (DWD)   │
                                          └─────────────────┘
```

## Status

🚧 **Planning phase** — API research complete, implementation not started.

See [docs/API_RESEARCH.md](docs/API_RESEARCH.md) for detailed integration options.

## Quick Start (once implemented)

```bash
npm install
npm run build

# Add to mcporter config:
# "mtb": { "command": "node /path/to/mtb-mcp/dist/index.js" }
```

## License

MIT
