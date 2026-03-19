# TrailPilot REST API — Schnittstellenvereinbarung v1.0

**Datum:** 2026-03-19
**Scope:** Frontend (Webapp) ↔ Backend (FastAPI)
**Basis:** mtb-mcp Tools + Pydantic Models

---

## 1. Allgemeines

### 1.1 Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://trailpilot.local/api/v1
```

### 1.2 Konventionen

| Regel | Beschreibung |
|-------|-------------|
| **Format** | JSON (application/json), UTF-8 |
| **Methoden** | GET für Reads, POST für Creates/Actions, PUT für Updates, DELETE für Deletes |
| **Naming** | snake_case für JSON-Keys, kebab-case für URL-Pfade |
| **Pagination** | `?limit=N&offset=M` — Default limit=20, max=100 |
| **Fehler** | Einheitliches Error-Objekt (siehe 1.4) |
| **Zeitstempel** | ISO 8601 UTC (`2026-03-19T14:30:00Z`) |
| **Koordinaten** | `lat`/`lon` als Float (WGS84) |
| **Distanzen** | Kilometer (km) für Strecken, Meter (m) für Höhe/Trails |
| **IDs** | UUID v4 für interne Entitäten, externe IDs als String |

### 1.3 Default Location

Wenn `lat`/`lon` nicht angegeben: Home-Location aus Server-Config (Eckental/Forth: 49.5833, 11.2333).

### 1.4 Response-Envelope

**Erfolg:**
```json
{
  "status": "ok",
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "duration_ms": 142,
    "timestamp": "2026-03-19T14:30:00Z"
  }
}
```

**Fehler:**
```json
{
  "status": "error",
  "error": {
    "code": "STRAVA_AUTH_MISSING",
    "message": "Strava credentials not configured",
    "details": null
  },
  "meta": { "request_id": "uuid", "timestamp": "..." }
}
```

**Error Codes:**

| Code | HTTP | Beschreibung |
|------|------|-------------|
| `VALIDATION_ERROR` | 422 | Ungültige Parameter |
| `NOT_FOUND` | 404 | Resource nicht gefunden |
| `AUTH_MISSING` | 401 | Credentials fehlen (Strava, Komoot, etc.) |
| `EXTERNAL_API_ERROR` | 502 | Externe API nicht erreichbar |
| `RATE_LIMITED` | 429 | Rate Limit überschritten |
| `INTERNAL_ERROR` | 500 | Unerwarteter Serverfehler |

### 1.5 WebSocket

```
ws://localhost:8000/api/v1/ws
```

Events (Server → Client):
```json
{"event": "timer_update", "data": {"remaining_minutes": 491, "status": "active"}}
{"event": "sensor_reading", "data": {"type": "heart_rate", "bpm": 142}}
{"event": "weather_alert", "data": {"severity": "moderate", "headline": "FROST"}}
```

---

## 2. Endpoints nach Domain

---

### 2.1 Dashboard

#### `GET /dashboard`

Aggregierter Dashboard-State — ein Call für alle Dashboard-Karten.

**Response:**
```json
{
  "ride_score": {
    "score": 90,
    "verdict": "Great",
    "weather_score": 38,
    "trail_score": 25,
    "wind_score": 15,
    "daylight_score": 12,
    "penalties": ["Temp < 5°C early morning: -2"]
  },
  "weather_current": {
    "temp_c": 12.4,
    "wind_speed_kmh": 11,
    "condition": "cloudy",
    "humidity_pct": 63,
    "precipitation_mm": 0.0
  },
  "trail_condition": {
    "surface": "dirt",
    "condition": "dry",
    "confidence": "high",
    "rain_48h_mm": 0.0
  },
  "weekend_preview": {
    "saturday": {"score": 100, "condition": "cloudy", "temp_range": "2-10"},
    "sunday": {"score": 90, "condition": "cloudy", "temp_range": "2-7"}
  },
  "next_service": {
    "component": "Chain",
    "bike_name": "Spectral",
    "wear_pct": 4,
    "km_remaining": 1445,
    "status": "good"
  },
  "active_timer": {
    "active": true,
    "remaining_minutes": 492,
    "ride_description": "Lillachquelle Runde"
  }
}
```

**Backend-Mapping:**
- `ride_score` → `intelligence/ride_score.py` → `calculate_ride_score()`
- `weather_current` → `clients/dwd.py` → `DWDClient.get_current_weather()`
- `trail_condition` → `intelligence/trail_condition.py` → `estimate_condition()`
- `weekend_preview` → `intelligence/weekend_planner.py` → `plan_weekend()`
- `next_service` → `storage/bike_garage.py` → `BikeGarage.get_worst_wear()`
- `active_timer` → SQLite `safety_timers` table

---

### 2.2 Wetter

#### `GET /weather/forecast`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Breitengrad |
| `lon` | float | Home | Längengrad |
| `hours` | int | 72 | Stunden Vorhersage |

**Response:**
```json
{
  "location_name": "GRAEFENBERG",
  "lat": 49.5833,
  "lon": 11.2333,
  "generated_at": "2026-03-19T08:04:00Z",
  "hours": [
    {
      "time": "2026-03-19T09:00:00Z",
      "temp_c": 8.5,
      "wind_speed_kmh": 11,
      "wind_gust_kmh": 22,
      "precipitation_mm": 0.0,
      "precipitation_probability": 5,
      "humidity_pct": 58,
      "condition": "cloudy"
    }
  ]
}
```

**Backend:** `DWDClient.get_forecast()` → `WeatherForecast`

---

#### `GET /weather/rain-radar`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Breitengrad |
| `lon` | float | Home | Längengrad |

**Response:**
```json
{
  "lat": 49.5833,
  "lon": 11.2333,
  "rain_next_60min": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  "rain_approaching": false,
  "eta_minutes": null
}
```

**Backend:** `DWDClient.get_rain_radar()` → `RainRadar`

---

#### `GET /weather/alerts`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Breitengrad |
| `lon` | float | Home | Längengrad |

**Response:**
```json
{
  "alerts": [
    {
      "event": "FROST",
      "severity": "minor",
      "headline": "Amtliche WARNUNG vor FROST",
      "description": "Es tritt leichter Frost um -1 °C auf.",
      "onset": "2026-03-18T23:00:00Z",
      "expires": "2026-03-19T08:00:00Z"
    }
  ]
}
```

**Backend:** `DWDClient.get_alerts()` → `list[WeatherAlert]`

---

#### `GET /weather/history`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Breitengrad |
| `lon` | float | Home | Längengrad |

**Response:**
```json
{
  "lat": 49.5833,
  "lon": 11.2333,
  "total_mm_48h": 0.0,
  "hourly_mm": [0, 0, 0, 0, 0, 0, ...],
  "last_rain_hours_ago": null
}
```

**Backend:** `DWDClient.get_rain_history()` → `RainHistory`

---

### 2.3 Trails

#### `GET /trails`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Zentrum |
| `lon` | float | Home | Zentrum |
| `radius_km` | float | 10 | Suchradius |
| `min_difficulty` | string? | null | Min. MTB-Scale (S0-S6) |
| `surface` | string? | null | Filter: dirt, gravel, rock, asphalt |
| `limit` | int | 50 | Max Ergebnisse |
| `offset` | int | 0 | Pagination |

**Response:**
```json
{
  "total": 313,
  "trails": [
    {
      "osm_id": 1268165932,
      "name": "Frängman",
      "mtb_scale": "S1",
      "surface": "dirt",
      "length_m": 277,
      "condition": {
        "status": "dry",
        "confidence": "high"
      },
      "geometry": [
        {"lat": 49.584, "lon": 11.234, "ele": 380},
        {"lat": 49.585, "lon": 11.235, "ele": 395}
      ]
    }
  ]
}
```

**Backend:** `OverpassClient.find_trails()` → `list[Trail]`, enriched mit `trail_condition.estimate_condition()` pro Surface-Typ

---

#### `GET /trails/{osm_id}`

**Response:**
```json
{
  "osm_id": 1268165932,
  "name": "Frängman",
  "mtb_scale": "S1",
  "surface": "dirt",
  "length_m": 277,
  "geometry": [...],
  "condition": {
    "status": "dry",
    "confidence": "high",
    "rain_48h_mm": 0.0,
    "hours_since_rain": null,
    "reasoning": "Low absorbed water (0.0mm) on dirt"
  }
}
```

**Backend:** `OverpassClient.get_trail_details()` + `trail_condition.estimate_condition()`

---

#### `GET /trails/condition`

Trail-Zustandsschätzung ohne spezifischen Trail.

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Standort |
| `lon` | float | Home | Standort |
| `surface` | string | "dirt" | Oberflächen-Typ |

**Response:**
```json
{
  "surface": "dirt",
  "condition": "dry",
  "confidence": "high",
  "rain_48h_mm": 0.0,
  "hours_since_rain": null,
  "temp_c": 8.5,
  "reasoning": "Low absorbed water (0.0mm) on dirt"
}
```

**Backend:** `intelligence/trail_condition.py` → `estimate_condition()`

---

### 2.4 Touren

#### `GET /tours/search`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `query` | string? | null | Suchbegriff |
| `lat` | float | Home | Zentrum |
| `lon` | float | Home | Zentrum |
| `radius_km` | float | 30 | Suchradius |
| `min_distance_km` | float? | null | Min. Tourlänge |
| `max_distance_km` | float? | null | Max. Tourlänge |
| `difficulty` | string? | null | easy, moderate, difficult, expert |
| `sources` | string? | "all" | komoot, gpstour, all |
| `limit` | int | 20 | Max Ergebnisse |

**Response:**
```json
{
  "total": 5,
  "tours": [
    {
      "id": "549100",
      "source": "komoot",
      "name": "Lillachquelle – Teufelstisch auf dem Eberhardsberg Runde von Eschenau",
      "distance_km": 38.5,
      "elevation_m": 920,
      "difficulty": "moderate",
      "region": null,
      "url": "https://www.komoot.com/de-de/smarttour/549100",
      "start_point": {"lat": 49.58, "lon": 11.22}
    }
  ]
}
```

**Backend:** `KomootClient.search_tours()` + `GPSTourClient.search()` + `tour_fusion.deduplicate_tours()`

---

#### `GET /tours/{source}/{tour_id}`

Tour-Details.

| Param | Typ | Beschreibung |
|-------|-----|-------------|
| `source` | path | "komoot" oder "gpstour" |
| `tour_id` | path | Tour-ID |

**Response:**
```json
{
  "id": "549100",
  "source": "komoot",
  "name": "Lillachquelle – Teufelstisch...",
  "distance_km": 38.5,
  "elevation_m": 920,
  "difficulty": "moderate",
  "url": "https://...",
  "description": "Tolle Runde durch die Fränkische Schweiz...",
  "duration_minutes": 180,
  "surfaces": ["gravel", "dirt", "asphalt"],
  "waypoints": [{"lat": 49.58, "lon": 11.22, "ele": 350}, ...],
  "download_count": 1234,
  "rating": 4.5
}
```

**Backend:** `KomootClient.get_tour_details()` oder `GPSTourClient.get_details()` → `TourDetail`

---

#### `GET /tours/{source}/{tour_id}/gpx`

GPX-Datei Download.

**Response:** `application/gpx+xml` (Binary)

**Backend:** `KomootClient.download_gpx()` oder `GPSTourClient.download_gpx()`

---

### 2.5 Routing

#### `POST /routes/plan`

```json
{
  "start_lat": 49.5833,
  "start_lon": 11.2333,
  "end_lat": 49.6150,
  "end_lon": 11.1850,
  "profile": "mtb"
}
```

**Response:**
```json
{
  "distance_km": 6.1,
  "elevation_gain_m": 751,
  "elevation_loss_m": 749,
  "duration_minutes": 21,
  "source": "ors",
  "geometry": [{"lat": 49.583, "lon": 11.233, "ele": 350}, ...],
  "gpx": "<gpx>...</gpx>"
}
```

**Backend:** `BRouterClient` (Fallback: `ORSClient`) → `Route`

---

#### `POST /routes/loop`

```json
{
  "start_lat": 49.5833,
  "start_lon": 11.2333,
  "distance_km": 30,
  "difficulty": "moderate"
}
```

**Response:** Wie `POST /routes/plan`

---

#### `POST /routes/elevation-profile`

```json
{
  "points": [{"lat": 49.58, "lon": 11.23}, {"lat": 49.62, "lon": 11.19}]
}
```

**Response:**
```json
{
  "total_distance_km": 6.1,
  "elevation_gain_m": 751,
  "elevation_loss_m": 749,
  "min_elevation_m": 295,
  "max_elevation_m": 520,
  "points": [
    {"distance_km": 0.0, "elevation_m": 350},
    {"distance_km": 0.5, "elevation_m": 380},
    ...
  ]
}
```

**Backend:** `clients/brouter.py` oder `clients/ors.py` → `ElevationProfile`

---

### 2.6 Intelligence

#### `GET /intelligence/ride-score`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Standort |
| `lon` | float | Home | Standort |
| `ride_duration_hours` | float | 2.0 | Geplante Ride-Dauer |
| `start_hour` | int? | jetzt | Startzeit (0-23) |

**Response:**
```json
{
  "score": 90,
  "verdict": "Great",
  "components": {
    "weather": {"score": 38, "max": 40, "penalties": ["-2: Temp < 5°C"]},
    "trail": {"score": 25, "max": 30, "surface": "dirt", "condition": "dry"},
    "wind": {"score": 15, "max": 15, "avg_kmh": 11, "gust_kmh": 22},
    "daylight": {"score": 12, "max": 15, "overlap_pct": 80}
  },
  "recommendation": "Get out there — great riding conditions!"
}
```

**Backend:** `intelligence/ride_score.py` → `calculate_ride_score()`

---

#### `GET /intelligence/weekend-plan`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Standort |
| `lon` | float | Home | Standort |
| `radius_km` | float | 20 | Tour-Suchradius |

**Response:**
```json
{
  "best_day": "saturday",
  "saturday": {
    "score": 100,
    "weather": {"temp_range": "2-10", "condition": "cloudy", "wind_kmh": 11},
    "trail_condition": "dry",
    "tours": [
      {"id": "549100", "source": "komoot", "name": "Lillachquelle...", "distance_km": 38.5}
    ]
  },
  "sunday": {
    "score": 90,
    "weather": {"temp_range": "2-7", "condition": "cloudy", "wind_kmh": 8},
    "trail_condition": "dry",
    "tours": [...]
  }
}
```

**Backend:** `intelligence/weekend_planner.py` → `plan_weekend()`

---

#### `POST /intelligence/auto-tag`

GPS-Trace gegen bekannte Trails matchen.

```json
{
  "gpx_data": "<gpx>...</gpx>",
  "activity_id": null
}
```

**Response:**
```json
{
  "matches": [
    {
      "trail_name": "Frängman",
      "osm_id": 1268165932,
      "mtb_scale": "S1",
      "overlap_pct": 87.5,
      "distance_avg_m": 12.3
    }
  ],
  "segments": [
    {"start_index": 0, "end_index": 45, "trail_name": "Frängman", "difficulty": "S1"}
  ]
}
```

**Backend:** `intelligence/trail_tagger.py` → `match_trails()` + `tag_ride_segments()`

---

### 2.7 Strava

#### `GET /strava/activities`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `limit` | int | 20 | Max Ergebnisse |
| `sport_type` | string? | "MountainBikeRide" | Filter (null=alle) |

**Response:**
```json
{
  "activities": [
    {
      "id": 12345678,
      "name": "Hetzlas Runde",
      "sport_type": "MountainBikeRide",
      "distance_km": 42.3,
      "elevation_gain_m": 850,
      "moving_time_seconds": 7200,
      "start_date": "2026-03-15T10:30:00Z",
      "average_speed_kmh": 18.5,
      "average_heartrate": 145,
      "average_watts": 220
    }
  ]
}
```

**Backend:** `StravaClient.get_recent_activities()` → `list[ActivitySummary]`

---

#### `GET /strava/activities/{activity_id}`

**Response:** Wie oben + `segment_efforts`, `description`, `device_name`

**Backend:** `StravaClient.get_activity_details()` → `ActivityDetail`

---

#### `GET /strava/activities/{activity_id}/gpx`

**Response:** `application/gpx+xml`

**Backend:** `StravaClient.export_gpx()`

---

#### `GET /strava/stats`

**Response:**
```json
{
  "recent_ride_totals": {"count": 12, "distance_km": 450, "elevation_gain_m": 8500, "moving_time_seconds": 72000},
  "ytd_ride_totals": {"count": 45, "distance_km": 1800, "elevation_gain_m": 32000, "moving_time_seconds": 288000},
  "all_ride_totals": {"count": 320, "distance_km": 12500, "elevation_gain_m": 220000, "moving_time_seconds": 1800000}
}
```

**Backend:** `StravaClient.get_athlete_stats()` → `AthleteStats`

---

#### `GET /strava/segments/explore`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `lat` | float | Home | Zentrum |
| `lon` | float | Home | Zentrum |
| `radius_km` | float | 10 | Suchradius |

**Response:**
```json
{
  "segments": [
    {
      "id": 98765,
      "name": "Hetzlas Climb",
      "distance_m": 2340,
      "average_grade": 6.2,
      "elevation_high": 520,
      "elevation_low": 380,
      "climb_category": 3
    }
  ]
}
```

**Backend:** `StravaClient.explore_segments()` → `list[SegmentInfo]`

---

#### `GET /strava/weekly-summary`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `weeks` | int | 1 | Anzahl Wochen |

**Response:**
```json
{
  "weeks": [
    {
      "start_date": "2026-03-10",
      "end_date": "2026-03-16",
      "ride_count": 3,
      "total_distance_km": 112,
      "total_elevation_m": 2100,
      "total_duration_seconds": 18000,
      "avg_speed_kmh": 17.8
    }
  ]
}
```

**Backend:** `StravaClient.get_weekly_summary()`

---

### 2.8 Bike Garage

#### `GET /bikes`

**Response:**
```json
{
  "bikes": [
    {
      "id": "uuid",
      "name": "Canyon Spectral",
      "brand": "Canyon",
      "model": "Spectral 29 CF",
      "type": "mtb",
      "total_km": 1247,
      "total_hours": 86,
      "component_count": 7,
      "worst_wear_pct": 4,
      "worst_wear_component": "Chain"
    }
  ]
}
```

**Backend:** `BikeGarage.get_bikes()`

---

#### `GET /bikes/{bike_id}/components`

**Response:**
```json
{
  "bike_name": "Canyon Spectral",
  "components": [
    {
      "id": "uuid",
      "type": "chain",
      "type_display": "Chain",
      "brand": "Shimano",
      "model": "XT CN-M8100",
      "installed_date": "2026-03-19",
      "installed_km": 0,
      "current_effective_km": 55,
      "current_hours": 2.5,
      "service_interval_km": 1500,
      "wear_pct": 4,
      "km_remaining": 1445,
      "status": "good"
    }
  ]
}
```

**Backend:** `BikeGarage.get_components()` + `WearEngine.calculate_wear()`

---

#### `POST /bikes/{bike_id}/components`

```json
{
  "type": "chain",
  "brand": "Shimano",
  "model": "XT CN-M8100",
  "installed_km": 0
}
```

**Response:** Die erstellte Komponente (wie oben)

**Backend:** `BikeGarage.add_component()`

---

#### `POST /bikes/{bike_id}/rides`

```json
{
  "distance_km": 42.0,
  "duration_hours": 2.5,
  "terrain": "S2",
  "weather": "damp",
  "avg_power_watts": 220,
  "strava_activity_id": null
}
```

**Response:**
```json
{
  "actual_km": 42.0,
  "effective_km": 55.4,
  "terrain_modifier": 1.2,
  "weather_modifier": 1.1,
  "intensity_modifier": 1.0,
  "components_updated": 3
}
```

**Backend:** `WearEngine.calculate_effective_km()` + `BikeGarage.log_ride()`

---

#### `POST /bikes/{bike_id}/service`

```json
{
  "component_type": "chain",
  "service_type": "replace",
  "notes": "Shimano XT CN-M8100 ersetzt"
}
```

**Response:**
```json
{
  "component": "Chain",
  "service_type": "replace",
  "wear_reset": true,
  "previous_wear_pct": 78,
  "timestamp": "2026-03-19T14:30:00Z"
}
```

**Backend:** `BikeGarage.log_service()`

---

### 2.9 Training & Fitness

#### `GET /training/goals`

**Response:**
```json
{
  "goals": [
    {
      "id": "uuid",
      "name": "Alpencross Ischgl-Riva",
      "type": "alpencross",
      "target_date": "2026-07-15",
      "target_distance_km": 400,
      "target_elevation_m": 12000,
      "days_remaining": 118,
      "status": "active",
      "current_phase": "base",
      "total_weeks": 16,
      "current_week": 1
    }
  ]
}
```

**Backend:** `TrainingStore.get_goals()`

---

#### `POST /training/goals`

```json
{
  "name": "Alpencross Ischgl-Riva",
  "type": "alpencross",
  "target_date": "2026-07-15",
  "target_distance_km": 400,
  "target_elevation_m": 12000,
  "description": "5-Tage Alpenüberquerung via Reschenpass"
}
```

**Response:** Das erstellte Goal (wie oben) + generierter Trainingsplan

**Backend:** `TrainingStore.add_goal()` + `TrainingPlanner.generate_plan()`

---

#### `GET /training/goals/{goal_id}/plan`

**Response:**
```json
{
  "goal_name": "Alpencross Ischgl-Riva",
  "target_date": "2026-07-15",
  "weeks": [
    {
      "week_number": 16,
      "phase": "base",
      "is_current": true,
      "planned_hours": 3.0,
      "planned_km": 54,
      "planned_elevation_m": 1200,
      "intensity_focus": "base",
      "key_workout": "Long ride 3-4h, steady pace, moderate climbing"
    }
  ]
}
```

**Backend:** `TrainingStore.get_weeks()` → `list[TrainingWeek]`

---

#### `PUT /training/goals/{goal_id}/plan`

Plan anpassen (Krankheit, Urlaub).

```json
{
  "adjustment": "illness",
  "affected_weeks": [14, 13],
  "notes": "Erkältung, 2 Wochen Pause"
}
```

**Response:** Aktualisierter Plan

**Backend:** `TrainingPlanner.adjust_plan()`

---

#### `GET /training/fitness`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `days` | int | 90 | Zeitraum für Trend |

**Response:**
```json
{
  "current": {
    "ctl": 30,
    "atl": 25,
    "tsb": 5,
    "status": "fresh"
  },
  "trend": [
    {"date": "2026-03-19", "ctl": 30, "atl": 25, "tsb": 5},
    {"date": "2026-03-18", "ctl": 29, "atl": 24, "tsb": 5}
  ],
  "weekly_volume": {
    "km": 42,
    "elevation_m": 850,
    "hours": 2.5,
    "rides": 1
  }
}
```

**Backend:** `FitnessTracker.get_fitness()` → `FitnessSnapshot` + historische Daten

---

#### `GET /training/race-readiness`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `goal_id` | string? | null | Spezifisches Ziel |

**Response:**
```json
{
  "goal_name": "Alpencross Ischgl-Riva",
  "ready": false,
  "readiness_pct": 35,
  "checklist": [
    {"criterion": "CTL >= 80", "current": 30, "target": 80, "met": false},
    {"criterion": "Weekly elevation >= 3000m", "current": 850, "target": 3000, "met": false},
    {"criterion": "Longest ride >= 80km", "current": 42, "target": 80, "met": false},
    {"criterion": "Back-to-back rides", "current": 0, "target": 2, "met": false}
  ]
}
```

**Backend:** `intelligence/training_planner.py` → `check_readiness()`

---

### 2.10 eBike

#### `POST /ebike/range-check`

```json
{
  "battery_wh": 625,
  "charge_pct": 80,
  "assist_mode": "tour",
  "rider_kg": 85,
  "bike_kg": 25,
  "route": {
    "distance_km": 50,
    "elevation_gain_m": 1200,
    "points": null
  }
}
```

**Response:**
```json
{
  "can_finish": false,
  "available_wh": 500.0,
  "estimated_consumption_wh": 819.7,
  "remaining_wh": -319.7,
  "remaining_pct": -51.2,
  "consumption_per_km": 16.4,
  "estimated_range_km": 30.5,
  "safety_margin_pct": 10.0,
  "mode_comparison": {
    "eco": {"can_finish": true, "range_km": 62.5, "consumption_wh": 630.5},
    "tour": {"can_finish": false, "range_km": 30.5, "consumption_wh": 819.7},
    "emtb": {"can_finish": false, "range_km": 19.1, "consumption_wh": 1311.5},
    "turbo": {"can_finish": false, "range_km": 13.8, "consumption_wh": 1803.3}
  }
}
```

**Backend:** `intelligence/ebike_range.py` → `calculate_range()` für jeden Modus

---

### 2.11 Safety

#### `POST /safety/timer`

```json
{
  "expected_return_minutes": 180,
  "ride_description": "Lillachquelle Runde ab Forth",
  "emergency_contact": "Anna 0170-1234567"
}
```

**Response:**
```json
{
  "timer_id": "uuid",
  "expected_return": "2026-03-19T18:00:00Z",
  "status": "active",
  "remaining_minutes": 180
}
```

**Backend:** SQLite `safety_timers` INSERT

---

#### `GET /safety/timer`

**Response:**
```json
{
  "active": true,
  "timer_id": "uuid",
  "status": "active",
  "expected_return": "2026-03-19T18:00:00Z",
  "remaining_minutes": 145,
  "ride_description": "Lillachquelle Runde ab Forth",
  "emergency_contact": "Anna 0170-1234567",
  "strava_activity_found": false
}
```

Statuswerte: `active`, `overdue`, `cleared`

**Backend:** SQLite Query + `StravaClient` Activity Check

---

#### `DELETE /safety/timer/{timer_id}`

Timer manuell beenden.

**Response:**
```json
{"timer_id": "uuid", "status": "cleared", "cleared_at": "2026-03-19T16:30:00Z"}
```

---

#### `GET /safety/timer/history`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `limit` | int | 10 | Max Einträge |

**Response:**
```json
{
  "timers": [
    {
      "timer_id": "uuid",
      "ride_description": "Lillachquelle Runde",
      "created_at": "2026-03-19T12:00:00Z",
      "expected_return": "2026-03-19T18:00:00Z",
      "status": "cleared"
    }
  ]
}
```

---

### 2.12 BLE Sensoren

#### `GET /sensors/scan`

| Param | Typ | Default | Beschreibung |
|-------|-----|---------|-------------|
| `timeout` | float | 10.0 | Scan-Dauer in Sekunden |

**Response:**
```json
{
  "devices": [
    {
      "name": "TyreWiz Front",
      "address": "AA:BB:CC:DD:EE:FF",
      "rssi": -65,
      "sensor_type": "tire_pressure"
    }
  ],
  "scan_duration_seconds": 10.0
}
```

**Backend:** `ble/scanner.py` → `scan_sensors()`

---

#### `GET /sensors/tire-pressure`

**Response:**
```json
{
  "front_bar": 1.8,
  "front_psi": 26.1,
  "rear_bar": 2.0,
  "rear_psi": 29.0,
  "front_temp_c": 22.5,
  "rear_temp_c": 21.8,
  "timestamp": "2026-03-19T14:30:00Z"
}
```

**Backend:** `ble/tyrewiz.py` → `read_tire_pressure()`

---

### 2.13 System & Config

#### `GET /config`

Aktuelle Server-Konfiguration (nur nicht-sensitive Werte).

**Response:**
```json
{
  "home_lat": 49.5833,
  "home_lon": 11.2333,
  "default_radius_km": 30.0,
  "services": {
    "strava": {"configured": false},
    "komoot": {"configured": true},
    "gpstour": {"configured": true},
    "ors": {"configured": true},
    "brouter": {"available": false},
    "searxng": {"available": true, "url": "http://localhost:17888"},
    "intervals_icu": {"configured": false}
  }
}
```

---

#### `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "services": {
    "dwd": "ok",
    "overpass": "ok",
    "ors": "ok",
    "searxng": "ok",
    "brouter": "unavailable",
    "sqlite": "ok"
  }
}
```

---

## 3. Datentypen Referenz

### Enums

| Enum | Werte |
|------|-------|
| `WeatherCondition` | clear, cloudy, rain, heavy_rain, snow, thunderstorm, fog |
| `MTBScale` | S0, S1, S2, S3, S4, S5, S6 |
| `TrailSurface` | asphalt, gravel, dirt, grass, rock, roots, sand |
| `TrailConditionStatus` | dry, damp, wet, muddy, frozen |
| `TourSource` | komoot, gps_tour, mtb_project |
| `TourDifficulty` | easy, moderate, difficult, expert |
| `ComponentType` | chain, cassette, brake_pads_front, brake_pads_rear, tire_front, tire_rear, fork, shock, bottom_bracket, dropper, sealant, brake_fluid |
| `GoalType` | alpencross, xc_race, enduro_race, marathon, personal_challenge |
| `TrainingPhase` | base, build, peak, taper |
| `AssistMode` | eco, tour, emtb, turbo |
| `SensorType` | heart_rate, power_meter, speed_cadence, tire_pressure |
| `TimerStatus` | active, overdue, cleared |

### Shared Objects

**GeoPoint:**
```json
{"lat": 49.5833, "lon": 11.2333, "ele": 350.0}
```

**WearStatus (component status):**
- `good`: wear_pct < 50
- `warning`: wear_pct 50-80
- `critical`: wear_pct > 80

---

## 4. Frontend → Backend Mapping

| Screen | Primary Endpoint | Refresh-Interval |
|--------|-----------------|-----------------|
| Dashboard | `GET /dashboard` | 5 min |
| Touren | `GET /tours/search` | On demand |
| Tour-Detail | `GET /tours/{source}/{id}` | On demand |
| Trails | `GET /trails` | 15 min |
| Trail-Detail | `GET /trails/{osm_id}` | On demand |
| Wetter | `GET /weather/forecast` | 30 min |
| Rain Radar | `GET /weather/rain-radar` | 5 min |
| Alerts | `GET /weather/alerts` | 15 min |
| Bike Garage | `GET /bikes` + `GET /bikes/{id}/components` | On demand |
| Log Ride | `POST /bikes/{id}/rides` | — |
| Training | `GET /training/goals` + `GET /training/fitness` | 1h |
| Trainingsplan | `GET /training/goals/{id}/plan` | On demand |
| eBike Check | `POST /ebike/range-check` | — |
| Safety Timer | `GET /safety/timer` via WebSocket | Live |
| BLE Sensoren | `GET /sensors/scan` | On demand |

---

## 5. Implementierungs-Hinweise

### 5.1 Backend-Architektur

```python
# api/main.py
from fastapi import FastAPI
from mtb_mcp.clients.dwd import DWDClient    # WIEDERVERWENDUNG
from mtb_mcp.intelligence.ride_score import calculate_ride_score  # WIEDERVERWENDUNG

app = FastAPI(title="TrailPilot API", version="0.1.0")

@app.get("/api/v1/intelligence/ride-score")
async def ride_score_endpoint(lat: float = 49.5833, lon: float = 11.2333):
    # Gleicher Code wie MCP-Tool, nur als REST
    client = DWDClient()
    forecast = await client.get_forecast(lat, lon)
    score = calculate_ride_score(forecast, ...)
    return {"status": "ok", "data": score}
```

### 5.2 CORS

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

### 5.3 Caching

| Daten | TTL | Strategie |
|-------|-----|-----------|
| Wetter-Forecast | 30 min | Server-Cache |
| Trail-Liste | 24h | Server-Cache + ETag |
| Tour-Suche | 7 Tage | Server-Cache |
| Ride Score | 5 min | Server-Cache |
| Bike Garage | 0 | Kein Cache (DB live) |
| Strava Activities | 1h | Server-Cache |

### 5.4 Authentication (Phase 2)

Für die erste Version: kein Auth (lokaler Single-User).
Später: JWT Token + Session für Multi-User.

### 5.5 Test-Strategie

| Layer | Tool | Was |
|-------|------|-----|
| Unit Tests | pytest | 939 existierende Tests für Business-Logik |
| API Tests | pytest + httpx | FastAPI TestClient gegen jeden Endpoint |
| E2E Tests | Playwright | Webapp im Browser, klickt durch alle Screens |
| Contract Tests | pydantic | Response-Modelle validieren Request/Response |
