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
| Auth | JWT + bcrypt + Fernet | Multi-User, Strava OAuth, Email/PW |
| Wetter | DWD OpenData | Forecast, Regenradar, Alerts |
| Trails | OSM Overpass | MTB Trail-Katalog |
| Touren | Komoot + GPS-Tour.info | Multi-Source Tour-Suche |
| Tracking | Strava API v3 | Activities, Segments, GPX |
| Routing | BRouter (self-hosted) | MTB-optimierte Routen |
| Storage | SQLite (aiosqlite) | Bike Garage, Cache, History |
| Intelligence | Custom Algorithmen | Ride Score, Wear Engine, Trail Condition |
| Trainer | Invite-Links + Roles | Trainer sieht Athleten-Daten read-only |

---

## Tech Stack

```yaml
Backend: Python 3.12+, Poetry, FastMCP
HTTP: httpx + tenacity (retry)
Models: Pydantic v2 + pydantic-settings
Storage: SQLite via aiosqlite (~/.mtb-mcp/mtb.db)
Auth: PyJWT (HS256) + bcrypt + Fernet (token encryption)
Logging: structlog
Docker: BRouter (17777) + SearXNG (17888)
Testing: pytest + respx (httpx mocking)
Quality: Ruff + MyPy (strict)

Frontend: Next.js 16, React 19, TypeScript
Styling: Tailwind CSS v4 (@theme inline in globals.css)
Data Fetching: SWR (useApi hook)
Auth: AuthContext + localStorage JWT + 401 auto-refresh
E2E Testing: Playwright
```

---

## Development Workflow

### Quick Commands
```bash
# Backend
make dev          # Install + dev deps + pre-commit hooks
make run          # Start MCP server (stdio)
make test-unit    # Run unit tests
make test-api     # API integration tests
make lint         # Ruff check
make type-check   # MyPy strict
make quality      # lint + type-check
make docker-up    # Start BRouter + SearXNG

# Frontend (webapp/)
make webapp-install  # npm install
make webapp-dev      # Next.js dev server (port 3000)
make webapp-build    # Production build
make webapp-test     # Playwright E2E tests

# Combined
make test-all     # unit + api + e2e
```

### Code Quality
- **1 Feature = 1 Commit** (Atomic Rollbacks)
- `make quality` before every commit (Backend)
- `cd webapp && npx next build` before every commit (Frontend)
- Ruff line-length=100, select E/W/F/I/B/SIM
- MyPy strict mode

### Frontend Architecture (webapp/)

```
webapp/src/
  app/                    # Next.js App Router (file-based routing)
    layout.tsx            # Shell: AuthProvider + Header + BottomNav
    page.tsx              # Dashboard (auth required)
    login/page.tsx        # Strava OAuth + Email/PW Login
    register/page.tsx     # Email/PW Registration
    auth/callback/page.tsx # Strava OAuth callback handler
    setup/page.tsx        # Onboarding: Location + first Bike
    profile/page.tsx      # User profile, Strava status, Trainer invite
    trainer/page.tsx      # "Meine Athleten" list
    trainer/[athleteId]/  # Athlete detail (read-only fitness/goals)
    weather/page.tsx      # Forecast, Radar, Alerts, History
    trails/page.tsx       # Trail search + filter chips
    trails/[osmId]/       # Trail detail
    tours/page.tsx        # Tour search + radius slider
    tours/[source]/[id]/  # Tour detail + GPX download
    bike/page.tsx         # Bike Garage CRUD (auth required)
    training/page.tsx     # CTL/ATL/TSB + Goals + Plans (auth required)
    ebike/page.tsx        # Range Check calculator
    safety/page.tsx       # Safety Timer CRUD (auth required)
  contexts/
    AuthContext.tsx        # AuthProvider, useAuth() hook, JWT in localStorage
  components/
    ProtectedRoute.tsx     # Redirect to /login if !user
    ui/                   # Primitives (Card, Badge, Modal, etc.)
  lib/
    api.ts                # Typed fetch() + JWT header + 401 auto-refresh
    types.ts              # TypeScript interfaces (from API_SPEC.md)
  hooks/
    useApi.ts             # SWR-based data fetching hook
  e2e/                    # Playwright test specs (9 files, ~47 tests)
```

**Key patterns:**
- All pages are `'use client'` components using `useApi()` hook
- API client at `lib/api.ts` wraps `fetch()` with JWT auth header + 401 refresh
- `AuthProvider` in layout.tsx manages user session via localStorage
- Protected pages wrapped with `<ProtectedRoute>` → redirect to /login
- Design tokens in `globals.css` via Tailwind v4 `@theme inline`
- Dark theme: bg-bg-primary (#0f0f1e), bg-bg-card (#1a1a2e)

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

## Test Pyramid

| Tier | Location | Count | Framework |
|------|----------|-------|-----------|
| Unit | `tests/unit/` | 939+ | pytest + respx |
| API Integration | `tests/integration/` | 32 | pytest + httpx ASGI |
| E2E | `webapp/e2e/` | 47 | Playwright |

**API Integration Tests** use `httpx.ASGITransport` to test FastAPI endpoints
in-process (no server needed). External APIs mocked via `unittest.mock.patch`.

**E2E Tests** use Playwright route interception (`page.route()`) to mock API
responses. Next.js dev server starts automatically via `playwright.config.ts`.

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
# Auth (required for multi-user)
MTB_MCP_JWT_SECRET=               # HS256 secret
MTB_MCP_TOKEN_ENCRYPTION_KEY=     # Fernet key for Strava token encryption
MTB_MCP_STRAVA_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback

# General
MTB_MCP_LOG_LEVEL=INFO
MTB_MCP_HOME_LAT=49.59      # Default search center
MTB_MCP_HOME_LON=11.00
MTB_MCP_STRAVA_CLIENT_ID=    # Strava OAuth (app-level)
MTB_MCP_STRAVA_CLIENT_SECRET=
MTB_MCP_KOMOOT_EMAIL=        # Komoot Basic Auth
MTB_MCP_ORS_API_KEY=         # OpenRouteService
MTB_MCP_BROUTER_URL=http://localhost:17777
MTB_MCP_SEARXNG_URL=http://localhost:17888
```

See `.env.template` for all variables.

### Auth Architecture

| Endpoint | Auth | Beschreibung |
|----------|------|-------------|
| weather, trails, tours, routing, intelligence, ebike, system | Public | Kein Auth nötig |
| bikes, training, safety, strava, dashboard | Protected | `Depends(get_current_user)` |
| /auth/* | Mixed | Login/Register public, /me protected |
| /trainer/* | Protected | Trainer-System mit Invite-Links |

**Auth-Paket:** `src/mtb_mcp/auth/`
- `jwt.py` — Access (60min) + Refresh (30d) Tokens, HS256
- `encryption.py` — Fernet für Strava-Token-at-rest
- `strava_oauth.py` — OAuth2 Code Exchange
- `dependencies.py` — `get_current_user()` FastAPI Dependency
- `models.py` — User, TokenPair, Request/Response Models

**Storage:** `src/mtb_mcp/storage/user_store.py` — Users, Trainer Relations, Invites, Refresh Tokens

**DB-Migrationen 10–15:** users, trainer_relationships, refresh_tokens, invite_links, user_id auf Datentabellen, fitness_snapshots composite PK

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
