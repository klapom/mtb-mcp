# API Research — Integrationsmöglichkeiten

## Übersicht

| Datenquelle | API? | Auth | MTB-spezifisch | Echtzeit-Bedingungen | Routing | Aufwand |
|-------------|------|------|----------------|---------------------|---------|---------|
| **Strava** | ✅ MCP existiert | OAuth2 | ✅ (Activities/Segments) | ⚠️ indirekt | ❌ | Gering |
| **Komoot** | ⚠️ Reverse-Engineered | Basic Auth | ✅ Tour-Suche | ❌ | ✅ | Mittel |
| **OSM/Overpass** | ✅ Frei | Keine | ✅ mtb:scale Tags | ❌ statisch | ❌ | Gering |
| **OpenRouteService** | ✅ Free Tier | API Key | ⚠️ nur Rad allgemein | ❌ | ✅ | Gering |
| **BRouter** | ✅ Self-hosted | Keine | ✅ MTB-Profile | ❌ | ✅ | Mittel |
| **DWD Wetter** | ✅ OpenData | Keine | ❌ | ✅ | ❌ | Gering |
| **GPS-Tour.info** | ⚠️ SearXNG+Scraping | Login (GPX) | ✅ 150k Tracks | ❌ | ❌ | Mittel |
| **Trailforks** | ❌ Keine API | — | ✅ | ✅ | ❌ | Nicht machbar |
| **AllTrails** | ❌ Keine API | — | ✅ | ⚠️ | ❌ | Nicht machbar |

---

## 1. Strava

### Status: ✅ MCP-Server existiert (`@r-huijts/strava-mcp-server`)

**Empfohlenes Paket:** `@r-huijts/strava-mcp-server` (25 Tools, Jan 2026, aktiv gepflegt)

### Verfügbare Tools (25)

**Athlet & Profil (5):**
`get-athlete-profile`, `get-athlete-stats`, `get-athlete-clubs`, `get-athlete-shoes`, `get-athlete-zones`

**Aktivitäten (7):**
`get-recent-activities`, `get-all-activities`, `get-activity-details`, `get-activity-laps`, `get-activity-photos`, `get-activity-streams` (Zeitreihen: Höhe, Kadenz, HF, Power, Speed)

**Segmente (7):**
`list-starred-segments`, `get-segment`, `explore-segments`, `star-segment`, `get-segment-effort`, `list-segment-efforts`, `get-segment-leaderboard`

**Routen (4):**
`list-athlete-routes`, `get-route`, `export-route-gpx` ✅, `export-route-tcx` ✅

### Auth: OAuth2

1. App registrieren auf `strava.com/settings/api` → Client ID + Secret
2. Redirect URI: `http://localhost:3000/auth/callback`
3. User autorisiert → Access Token (6h Gültigkeit) + Refresh Token
4. Tokens in `~/.strava-mcp/tokens.json`

**Scopes:** `read`, `read_all`, `activity:read`, `activity:read_all`, `activity:write`

### Rate Limits

- **15-Minuten-Fenster:** 200 Requests (100 non-upload)
- **Täglich:** 2.000 Requests (1.000 non-upload)
- **Reset:** Alle 15 Min (:00, :15, :30, :45) / täglich Mitternacht UTC

### MTB-relevante Endpoints

| Endpoint | Nutzen |
|----------|--------|
| `/athlete/activities` | Aktivitäten filtern nach `sport_type: MountainBikeRide` |
| `/activities/{id}/streams` | Höhenprofil, HF, Power, Kadenz |
| `/segments/explore` | Segmente nach Koordinaten entdecken |
| `/routes/{id}/export_gpx` | GPX-Export für GPS-Geräte |

### Installation

```bash
npm install @r-huijts/strava-mcp-server
# Oder in mcporter.json:
# "strava": { "command": "npx @r-huijts/strava-mcp-server" }
```

---

## 2. Komoot

### Status: ⚠️ Kein offizielles API — Reverse-Engineered v007 (stabil, weit verbreitet)

**Kein MCP-Server vorhanden — muss gebaut werden.**

Beste Grundlage: [kompy](https://github.com/Tsadoq/kompy) (Python, maintained)

### API Endpoints (v007)

| Endpoint | Methode | Zweck |
|----------|---------|-------|
| `api.komoot.de/v006/account/email/{email}` | GET | Login + Token |
| `api.komoot.de/v007/users/{user}/tours/` | GET | Tour-Liste mit Filtern |
| `api.komoot.de/v007/tours/{id}` | GET | Tour-Details (HAL+JSON) |
| `api.komoot.de/v007/tours/{id}.gpx` | GET | GPX-Download |
| `api.komoot.de/v007/tours/{id}.fit` | GET | FIT-Download |

### Verfügbare Daten

- **Metadaten:** Name, Distanz, Höhenmeter, Dauer, Schwierigkeit (easy/moderate/difficult)
- **Segmente:** Typ (Anstieg/Abstieg/Flach), Wegtyp (Asphalt/Schotter/Trail/Singletrack)
- **Oberflächen:** Asphalt, Schotter, Erde, Gras, Sand, Fels
- **Koordinaten:** lat/lon mit Höhe pro Segment
- **Export:** GPX, FIT

### Such-Filter

```python
connector.get_tours(
    center="49.6, 11.1",       # Erlangen
    max_distance=50,            # km Umkreis
    sport_types=["mtb"],        # MTB-Touren
    status="public",            # öffentliche Touren
    sort_field="proximity"      # nach Nähe sortiert
)
```

### Auth

HTTP Basic Auth: `email:password` → einfach, kein OAuth-Overhead für private Nutzung.

### Geplante MCP-Tools

| Tool | Funktion |
|------|----------|
| `search_tours` | Tour-Suche nach Region, Distanz, Schwierigkeit, Sportart |
| `get_tour_details` | Metadaten + Höhenprofil |
| `download_tour_gpx` | GPX für Navigation/Garmin |

### Referenzen

- [Komoot API v007 Schema](https://static.komoot.de/doc/external-api/v007/index.html)
- [kompy (Python)](https://github.com/Tsadoq/kompy)
- [komoot-oauth2-connect-example](https://github.com/komoot/komoot-oauth2-connect-example)

---

## 3. OpenStreetMap / Overpass API

### Status: ✅ Frei, keine Auth, sofort nutzbar

### MTB-Tags in OSM

| Tag | Bedeutung | Werte |
|-----|-----------|-------|
| `mtb:scale` | Technische Schwierigkeit | 0-6 (IMBA-Standard) |
| `mtb:scale:uphill` | Kletterschwierigkeit | 0-5 |
| `mtb:scale:imba` | IMBA-Rating | green/blue/black/dh |
| `trail_visibility` | Sichtbarkeit/Pflege | excellent–horrible |
| `smoothness` | Oberfläche | excellent–impassable |
| `surface` | Belag | asphalt/gravel/dirt/rock |

### Beispiel-Query

```bash
# Alle MTB-Trails im Umkreis Erlangen
curl -X POST "https://overpass-api.de/api/interpreter" \
  --data '[bbox:49.5,10.9,49.7,11.2];way["mtb:scale"];out geom;'
```

### Limitierungen

- **Nur statische Daten** — keine Echtzeit-Bedingungen
- Datenqualität variiert je nach Region (Franken gut getaggt)
- Keine Routing-Funktion (nur Geometrie)

---

## 4. OpenRouteService (ORS)

### Status: ✅ Free Tier (40 req/min)

- **Endpoint:** `https://api.openrouteservice.org/v2/`
- **Auth:** Kostenloser API Key
- **MTB:** ⚠️ Kein dediziertes MTB-Profil — nur `cycling-regular`/`cycling-mountain`
- **Services:** Routing, Isochrone, Distanzmatrix

```bash
curl "https://api.openrouteservice.org/v2/directions/cycling-mountain?api_key=KEY&start=11.1,49.6&end=11.2,49.7"
```

---

## 5. BRouter

### Status: ✅ Open Source, Self-hosted

- **MTB-Profile:** `trekking`, `soft_steep_downhill` (DH-optimiert)
- **Zugang:** Öffentliche Instanz (`brouter.de`) nur Web-UI; API erfordert Self-Hosting
- **Docker:** Verfügbar für einfaches Deployment
- **Vorteil:** Echte MTB-optimierte Routenberechnung mit Höhendaten

---

## 6. DWD Wetter (geplant)

Bereits in NanoClaw MEMORY als Pending Topic:

- **Unwetterwarnungen:** `https://opendata.dwd.de/weather/alerts/` (CAP-Format)
- **Regenradar Nowcasting:** `https://opendata.dwd.de/weather/radar/` (alle 5 Min)
- **Use Case:** "Regen in ~20 Min an deinem Standort" → proaktive SuKI-Warnung

---

## 7. GPS-Tour.info

### Status: ⚠️ Keine API — aber über SearXNG + Scraping nutzbar

150.000+ GPS-Tracks (Europa, v.a. DACH). Kein offizielles API, aber:

### Zugriffswege

| Was | Methode | Auth |
|-----|---------|------|
| **Tour-Suche** | SearXNG (`site:gps-tour.info mountainbike Erlangen`) | Keine |
| **Tour-Metadaten** | Detail-Seite scrapen (`/de/touren/detail.{ID}.html`) | Keine |
| **GPX-Download** | Download-Seite (`/de/touren/download.{ID}.html`) | Login (Cookie) |

### Verfügbare Daten (ohne Login)

Aus SearXNG-Suchergebnissen:
- Titel, Kategorie (Mountainbike/Rennrad/Wandern)
- Länge (km), Höhenmeter (m)
- Region (Land, Bundesland, Ort, Gebiet)
- Tour-ID (für Detail-Link)

Aus Detail-Seite (HTML scraping):
- Beschreibungstext
- Höhenprofil (min/max Höhe)
- Download-Zähler (Popularität)
- Bewertungen
- Schwierigkeitshinweise

### GPX-Download (mit Login)

Erfordert Session-Cookie via Login:
```
POST /de/login.html
  username=...&password=...&redx_autologin=1
→ Session-Cookie

GET /de/touren/download.{ID}.html
→ GPX-Datei
```

### Scraping-Etikette

⚠️ GPS-Tour.info ist ein Community-Projekt — respektvolles Scraping ist Pflicht:

- **Rate Limiting:** Min. 3-5 Sekunden zwischen Requests
- **Randomisierung:** ±1-2s Jitter auf Wait-Times
- **User-Agent:** Ehrlicher UA mit Kontakt-Info
- **Caching:** Einmal geladene Tour-Daten lokal cachen (SQLite)
- **Kein Bulk-Download:** Nur on-demand wenn User konkret fragt
- **robots.txt beachten:** Vor Implementierung prüfen

### Geplante MCP-Tools

| Tool | Funktion | Auth |
|------|----------|------|
| `search_gpstour` | SearXNG-basierte Tour-Suche | Keine |
| `get_gpstour_details` | Metadaten von Detail-Seite scrapen | Keine |
| `download_gpstour_gpx` | GPX via Login-Session herunterladen | Login |

---

## Empfohlene Implementierungs-Reihenfolge

### Phase 1: Quick Wins (1-2 Tage)

1. **Strava MCP** einbinden — `@r-huijts/strava-mcp-server` in mcporter.json
2. **OSM Overpass** Tool — Trail-Katalog nach Region/Schwierigkeit
3. **Weather-Kombination** — vorhandenes weather-mcp für Ride-or-Not

### Phase 2: Komoot Integration (3-5 Tage)

4. **Komoot MCP** bauen — Python-Wrapper (kompy) oder Node.js direkt gegen v007
5. **Tour-Suche** + GPX-Export + WhatsApp-Versand (via send_file)

### Phase 3: Smart Features (optional)

6. **BRouter** self-hosted für MTB-Routing
7. **DWD Regenradar** für proaktive Warnungen
8. **Scheduled Tasks** — Wochenend-Empfehlungen, Post-Ride Analyse
