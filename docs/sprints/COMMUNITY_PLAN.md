# COMMUNITY_PLAN.md -- Vollstaendiger Implementierungsplan

## 1. Uebersicht

Drei zusammenhaengende Sub-Features fuer die Community-Funktionalitaet von TrailPilot:

1. **Community Rides** -- Offene Gruppenfahrten erstellen und beitreten
2. **Strava Community Invites** -- Strava-Freunde zu TrailPilot einladen
3. **Strava Data Import on Signup** -- Bestehende Strava-Daten beim Signup importieren

---

## 2. Datenbank-Migrationen

Alle neuen Tabellen werden als Migrationen 16-20 in `/home/admin/projects/mtb-mcp/src/mtb_mcp/storage/migrations.py` hinzugefuegt (aktuell letzter Stand: Migration 15).

**Migration 16: `community_rides` Tabelle**

```sql
CREATE TABLE IF NOT EXISTS community_rides (
    id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    tour_source TEXT,           -- 'komoot', 'gpstour', NULL fuer freie Routen
    tour_id TEXT,               -- ID bei tour_source, NULL wenn keine Tour verlinkt
    planned_date TEXT NOT NULL,  -- ISO date
    planned_time TEXT,           -- HH:MM (optional)
    meeting_point_lat REAL NOT NULL,
    meeting_point_lon REAL NOT NULL,
    meeting_point_name TEXT,
    max_participants INTEGER DEFAULT 10,
    difficulty TEXT DEFAULT 'S1', -- S0/S1/S2/S3/S4/S5
    distance_km REAL,
    elevation_m REAL,
    status TEXT DEFAULT 'open',  -- open/full/cancelled/completed
    visibility_radius_km REAL DEFAULT 50.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_community_rides_creator ON community_rides(creator_id);
CREATE INDEX idx_community_rides_status ON community_rides(status);
CREATE INDEX idx_community_rides_date ON community_rides(planned_date);
```

**Migration 17: `ride_participants` Tabelle**

```sql
CREATE TABLE IF NOT EXISTS ride_participants (
    id TEXT PRIMARY KEY,
    ride_id TEXT NOT NULL REFERENCES community_rides(id),
    user_id TEXT NOT NULL REFERENCES users(id),
    status TEXT DEFAULT 'requested',  -- requested/confirmed/declined/cancelled
    joined_at TEXT NOT NULL,
    UNIQUE(ride_id, user_id)
);
CREATE INDEX idx_ride_participants_ride ON ride_participants(ride_id);
CREATE INDEX idx_ride_participants_user ON ride_participants(user_id);
```

**Migration 18: `referral_links` Tabelle**

```sql
CREATE TABLE IF NOT EXISTS referral_links (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    token TEXT NOT NULL UNIQUE,
    source TEXT DEFAULT 'general',  -- strava_club/general/direct
    club_name TEXT,                 -- Strava Club Name fuer Kontext
    uses_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_referral_links_user ON referral_links(user_id);
CREATE INDEX idx_referral_links_token ON referral_links(token);
```

**Migration 19: `strava_import_status` zu users**

```sql
ALTER TABLE users ADD COLUMN strava_import_status TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN strava_import_started_at TEXT;
ALTER TABLE users ADD COLUMN strava_import_error TEXT;
```

**Migration 20: `strava_activities` Tabelle (Import-Cache)**

```sql
CREATE TABLE IF NOT EXISTS strava_activities (
    id INTEGER PRIMARY KEY,       -- Strava activity_id
    user_id TEXT NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    sport_type TEXT NOT NULL,
    distance_km REAL DEFAULT 0,
    elevation_gain_m REAL DEFAULT 0,
    moving_time_seconds INTEGER DEFAULT 0,
    start_date TEXT NOT NULL,
    average_speed_kmh REAL DEFAULT 0,
    average_heartrate REAL,
    average_watts REAL,
    suffer_score REAL,
    gear_id TEXT,
    imported_at TEXT NOT NULL,
    UNIQUE(id, user_id)
);
CREATE INDEX idx_strava_activities_user ON strava_activities(user_id);
CREATE INDEX idx_strava_activities_date ON strava_activities(start_date);
```

---

## 3. Neue Backend-Module

### 3a. Storage: `CommunityStore` (Neues Modul)

**Datei:** `/home/admin/projects/mtb-mcp/src/mtb_mcp/storage/community_store.py`

Folgt dem Muster von `BikeGarage` und `TrainingStore`:

```python
class CommunityStore:
    def __init__(self, db: Database) -> None: ...

    # Community Rides CRUD
    async def create_ride(...) -> CommunityRide: ...
    async def get_ride(ride_id: str) -> CommunityRide | None: ...
    async def list_nearby_rides(lat, lon, radius_km, date_from, date_to, difficulty, status) -> list[CommunityRide]: ...
    async def list_user_rides(user_id: str) -> list[CommunityRide]: ...  # created + joined
    async def update_ride_status(ride_id: str, status: str) -> None: ...
    async def cancel_ride(ride_id: str, creator_id: str) -> bool: ...

    # Participants
    async def request_join(ride_id: str, user_id: str) -> str: ...  # returns participant_id
    async def update_participant_status(ride_id, user_id, status, actor_id) -> bool: ...
    async def get_participants(ride_id: str) -> list[RideParticipant]: ...
    async def get_participant_count(ride_id: str) -> int: ...

    # Referral Links
    async def create_referral_link(user_id, source, club_name) -> tuple[str, str]: ...
    async def get_referral_link(token: str) -> dict | None: ...
    async def increment_referral_uses(token: str) -> None: ...
```

Die Geo-Filterung fuer `list_nearby_rides` nutzt eine Bounding-Box-Berechnung direkt in SQL (gleicher Ansatz wie `StravaClient.explore_segments`):

```sql
SELECT * FROM community_rides
WHERE status = 'open'
  AND planned_date >= ?
  AND meeting_point_lat BETWEEN ? AND ?
  AND meeting_point_lon BETWEEN ? AND ?
ORDER BY planned_date ASC
```

Danach im Python-Code die exakte Haversine-Distanz pruefen und nach `visibility_radius_km` filtern.

### 3b. Storage: `StravaImportStore` (Erweiterung in `user_store.py` oder eigenes Modul)

**Datei:** `/home/admin/projects/mtb-mcp/src/mtb_mcp/storage/strava_import_store.py`

```python
class StravaImportStore:
    def __init__(self, db: Database) -> None: ...

    async def update_import_status(user_id: str, status: str, error: str | None = None) -> None: ...
    async def get_import_status(user_id: str) -> dict | None: ...
    async def upsert_activity(user_id: str, activity: ActivitySummary) -> None: ...
    async def get_imported_activities(user_id: str, limit: int = 50) -> list[dict]: ...
    async def activity_exists(user_id: str, strava_id: int) -> bool: ...
```

### 3c. Pydantic Models (Neues Modul)

**Datei:** `/home/admin/projects/mtb-mcp/src/mtb_mcp/models/community.py`

```python
class CommunityRide(BaseModel):
    id: str
    creator_id: str
    creator_name: str          # JOINed from users
    creator_avatar: str | None
    title: str
    description: str | None
    tour_source: str | None
    tour_id: str | None
    planned_date: str          # ISO date
    planned_time: str | None
    meeting_point_lat: float
    meeting_point_lon: float
    meeting_point_name: str | None
    max_participants: int
    current_participants: int  # Computed
    difficulty: str
    distance_km: float | None
    elevation_m: float | None
    status: str
    created_at: str

class RideParticipant(BaseModel):
    id: str
    user_id: str
    display_name: str          # JOINed -- Privacy: nur Name + Avatar
    avatar_url: str | None
    status: str                # requested/confirmed/declined/cancelled
    joined_at: str

class RideCreateRequest(BaseModel):
    title: str
    description: str | None = None
    tour_source: str | None = None
    tour_id: str | None = None
    planned_date: str          # YYYY-MM-DD
    planned_time: str | None = None  # HH:MM
    meeting_point_lat: float
    meeting_point_lon: float
    meeting_point_name: str | None = None
    max_participants: int = 10
    difficulty: str = "S1"
    distance_km: float | None = None
    elevation_m: float | None = None
    visibility_radius_km: float = 50.0

class ParticipantUpdateRequest(BaseModel):
    status: str  # confirmed/declined

class ReferralLinkResponse(BaseModel):
    token: str
    url: str
    source: str
    club_name: str | None
    uses_count: int
```

### 3d. Strava Client Erweiterung

**Datei:** `/home/admin/projects/mtb-mcp/src/mtb_mcp/clients/strava.py` -- Neue Methoden hinzufuegen:

```python
# Neue Methoden in StravaClient:

async def get_athlete_clubs(self) -> list[dict[str, Any]]:
    """GET /athlete/clubs -- Liste der Clubs des Athleten."""
    return await self._authed_get_list("/athlete/clubs")

async def get_club_members(self, club_id: int) -> list[dict[str, Any]]:
    """GET /clubs/{id}/members -- Mitglieder eines Clubs."""
    return await self._authed_get_list(f"/clubs/{club_id}/members")

async def get_athlete_gear(self) -> list[dict[str, Any]]:
    """GET /athlete -- Gear aus Profil extrahieren."""
    data = await self._authed_get("/athlete")
    return data.get("bikes", []) + data.get("shoes", [])

async def get_activities_page(
    self, page: int = 1, per_page: int = 200, after: int | None = None,
) -> list[dict[str, Any]]:
    """GET /athlete/activities mit Paginierung fuer Bulk-Import."""
    params: dict[str, str] = {"per_page": str(per_page), "page": str(page)}
    if after is not None:
        params["after"] = str(after)
    return await self._authed_get_list("/athlete/activities", params=params)
```

**Wichtig:** Die Strava OAuth Scopes muessen `read,activity:read_all,profile:read_all` enthalten -- das ist bereits der Fall in `strava_oauth.py` (Zeile 28).

### 3e. Strava Import Service

**Datei:** `/home/admin/projects/mtb-mcp/src/mtb_mcp/services/strava_import.py`

```python
class StravaImportService:
    """Orchestriert den Strava-Datenimport nach Signup."""

    async def run_import(self, user_id: str) -> None:
        """Idempotenter Import: Activities, Gear, Fitness berechnen."""
        # 1. Status auf 'importing' setzen
        # 2. GET /athlete -- Gear holen
        # 3. Bikes in Garage anlegen (check strava_gear_id Duplikat)
        # 4. GET /athlete/activities paginiert -- letzte 200 Activities
        # 5. Activities in strava_activities upserten (UNIQUE check)
        # 6. Initiale CTL/ATL/TSB aus Activity-History berechnen
        # 7. Fitness Snapshots speichern
        # 8. Status auf 'done' setzen (oder 'failed' bei Fehler)
```

**Fitness-Berechnung:** Fuer jede importierte Activity wird ein approximierter TSS berechnet (basierend auf Duration und Intensitaet). Daraus CTL (42-Tage-Exponentialgewichtung) und ATL (7-Tage-Exponentialgewichtung). TSB = CTL - ATL.

---

## 4. Neue API Endpoints

### 4a. Community Rides Router

**Datei:** `/home/admin/projects/mtb-mcp/src/mtb_mcp/api/routes/community.py`

Registrierung in `main.py`:
```python
from mtb_mcp.api.routes import community
app.include_router(community.router, prefix="/api/v1/community", tags=["community"])
```

**Endpoints:**

| Method | Path | Auth | Beschreibung |
|--------|------|------|-------------|
| `POST` | `/rides` | JWT | Neuen Community Ride erstellen |
| `GET` | `/rides` | JWT | Offene Rides in der Naehe listen (Query: lat, lon, radius_km, date_from, date_to, difficulty) |
| `GET` | `/rides/mine` | JWT | Eigene Rides (erstellt + beigetreten) |
| `GET` | `/rides/{id}` | JWT | Ride-Detail inkl. Teilnehmer |
| `POST` | `/rides/{id}/join` | JWT | Beitrittsanfrage stellen |
| `PATCH` | `/rides/{id}/participants/{user_id}` | JWT | Teilnehmer bestaetigen/ablehnen (nur Creator) |
| `DELETE` | `/rides/{id}` | JWT | Ride absagen (nur Creator) |
| `POST` | `/invite-link` | JWT | Referral-Link generieren |
| `GET` | `/invite-link/{token}` | - | Referral-Link validieren (oeffentlich) |
| `GET` | `/clubs` | JWT | Strava Clubs des Users listen |
| `GET` | `/clubs/{club_id}/members` | JWT | Mitglieder eines Strava Clubs |

**Request/Response Shapes:**

`POST /rides` -- Request:
```json
{
  "title": "Feierabendrunde Rathsberg",
  "description": "Lockere Runde ueber S1 Trails",
  "tour_source": "komoot",
  "tour_id": "12345",
  "planned_date": "2026-04-05",
  "planned_time": "17:30",
  "meeting_point_lat": 49.59,
  "meeting_point_lon": 11.02,
  "meeting_point_name": "Parkplatz Rathsberg",
  "max_participants": 8,
  "difficulty": "S1",
  "distance_km": 25.5,
  "elevation_m": 450,
  "visibility_radius_km": 30.0
}
```

`POST /rides` -- Response:
```json
{
  "status": "ok",
  "data": {
    "id": "uuid...",
    "title": "Feierabendrunde Rathsberg",
    "creator_name": "Max M.",
    "status": "open",
    "current_participants": 0,
    "max_participants": 8,
    "planned_date": "2026-04-05",
    "planned_time": "17:30",
    "meeting_point_name": "Parkplatz Rathsberg"
  },
  "meta": { ... }
}
```

`GET /rides?lat=49.59&lon=11.0&radius_km=30&date_from=2026-04-01` -- Response:
```json
{
  "status": "ok",
  "data": [
    {
      "id": "uuid...",
      "creator_name": "Max M.",
      "creator_avatar": "https://...",
      "title": "Feierabendrunde Rathsberg",
      "planned_date": "2026-04-05",
      "planned_time": "17:30",
      "meeting_point_name": "Parkplatz Rathsberg",
      "difficulty": "S1",
      "distance_km": 25.5,
      "elevation_m": 450,
      "current_participants": 3,
      "max_participants": 8,
      "status": "open"
    }
  ],
  "total": 1,
  "meta": { ... }
}
```

`GET /rides/{id}` -- Response:
```json
{
  "status": "ok",
  "data": {
    "id": "uuid...",
    "creator_id": "uuid...",
    "creator_name": "Max M.",
    "creator_avatar": "https://...",
    "title": "Feierabendrunde Rathsberg",
    "description": "Lockere Runde ueber S1 Trails",
    "tour_source": "komoot",
    "tour_id": "12345",
    "planned_date": "2026-04-05",
    "planned_time": "17:30",
    "meeting_point_lat": 49.59,
    "meeting_point_lon": 11.02,
    "meeting_point_name": "Parkplatz Rathsberg",
    "difficulty": "S1",
    "distance_km": 25.5,
    "elevation_m": 450,
    "max_participants": 8,
    "current_participants": 3,
    "status": "open",
    "participants": [
      { "user_id": "...", "display_name": "Anna B.", "avatar_url": "...", "status": "confirmed" },
      { "user_id": "...", "display_name": "Tom K.", "avatar_url": null, "status": "requested" }
    ],
    "is_creator": true,
    "my_status": null
  },
  "meta": { ... }
}
```

`POST /rides/{id}/join` -- Response:
```json
{
  "status": "ok",
  "data": {
    "participant_id": "uuid...",
    "status": "requested",
    "message": "Beitrittsanfrage gesendet"
  }
}
```

`PATCH /rides/{id}/participants/{user_id}` -- Request:
```json
{ "status": "confirmed" }
```

`POST /invite-link` -- Request:
```json
{
  "source": "strava_club",
  "club_name": "MTB Franken"
}
```

`POST /invite-link` -- Response:
```json
{
  "status": "ok",
  "data": {
    "token": "abc123...",
    "url": "https://trailpilot.app/join/abc123...",
    "source": "strava_club",
    "club_name": "MTB Franken"
  }
}
```

### 4b. Strava Import Endpoints

Ergaenzt den bestehenden Auth-Router (`/api/v1/auth/`):

| Method | Path | Auth | Beschreibung |
|--------|------|------|-------------|
| `GET` | `/me/strava-import-status` | JWT | Import-Status abfragen |
| `POST` | `/me/strava-import` | JWT | Import manuell (erneut) ausloesen |

`GET /me/strava-import-status` -- Response:
```json
{
  "status": "ok",
  "data": {
    "import_status": "done",
    "started_at": "2026-03-20T14:30:00Z",
    "error": null,
    "activities_imported": 142,
    "bikes_imported": 2,
    "fitness_calculated": true
  }
}
```

---

## 5. Neue Frontend-Seiten und Komponenten

### 5a. TypeScript Types Erweiterung

**Datei:** `/home/admin/projects/mtb-mcp/webapp/src/lib/types.ts` -- Neue Interfaces:

```typescript
// Community Rides
export interface CommunityRide {
  id: string;
  creator_id: string;
  creator_name: string;
  creator_avatar: string | null;
  title: string;
  description: string | null;
  tour_source: string | null;
  tour_id: string | null;
  planned_date: string;
  planned_time: string | null;
  meeting_point_lat: number;
  meeting_point_lon: number;
  meeting_point_name: string | null;
  difficulty: string;
  distance_km: number | null;
  elevation_m: number | null;
  max_participants: number;
  current_participants: number;
  status: string;
  is_creator?: boolean;
  my_status?: string | null;
  participants?: RideParticipant[];
}

export interface RideParticipant {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  status: string;
  joined_at: string;
}

export interface StravaClub {
  id: number;
  name: string;
  member_count: number;
  sport_type: string;
  city: string;
  profile_medium: string;
}

export interface ReferralLink {
  token: string;
  url: string;
  source: string;
  club_name: string | null;
  uses_count: number;
}

export interface StravaImportStatus {
  import_status: string | null;
  started_at: string | null;
  error: string | null;
  activities_imported: number;
  bikes_imported: number;
  fitness_calculated: boolean;
}
```

### 5b. API Client Erweiterung

**Datei:** `/home/admin/projects/mtb-mcp/webapp/src/lib/api.ts` -- Neuer Namespace:

```typescript
export const Community = {
  listRides: (params?: { lat?: number; lon?: number; radius_km?: number; date_from?: string; difficulty?: string }) =>
    api<CommunityRide[]>(`/community/rides${qs(params ?? {})}`),
  myRides: () => api<CommunityRide[]>('/community/rides/mine'),
  getRide: (id: string) => api<CommunityRide>(`/community/rides/${id}`),
  createRide: (body: Omit<CommunityRide, 'id' | 'creator_id' | 'creator_name' | 'creator_avatar' | 'current_participants' | 'status'>) =>
    api<CommunityRide>('/community/rides', { method: 'POST', body: JSON.stringify(body) }),
  joinRide: (id: string) =>
    api<{ participant_id: string; status: string }>(`/community/rides/${id}/join`, { method: 'POST' }),
  updateParticipant: (rideId: string, userId: string, status: string) =>
    api<{ message: string }>(`/community/rides/${rideId}/participants/${userId}`, {
      method: 'PATCH', body: JSON.stringify({ status }),
    }),
  cancelRide: (id: string) =>
    api<{ message: string }>(`/community/rides/${id}`, { method: 'DELETE' }),
  createInviteLink: (source: string, clubName?: string) =>
    api<ReferralLink>('/community/invite-link', {
      method: 'POST', body: JSON.stringify({ source, club_name: clubName }),
    }),
  listClubs: () => api<StravaClub[]>('/community/clubs'),
};
```

### 5c. Neue Frontend-Seiten

| Route | Datei | Beschreibung |
|-------|-------|-------------|
| `/community` | `webapp/src/app/community/page.tsx` | Ride-Liste mit Filter (Radius, Datum, Schwierigkeit) |
| `/community/create` | `webapp/src/app/community/create/page.tsx` | Formular: Ride erstellen |
| `/community/{id}` | `webapp/src/app/community/[id]/page.tsx` | Ride-Detail mit Teilnehmerliste |

**`/community` (Ride-Liste):**
- Suchfilter: Radius-Slider (wie Touren-Seite), Datum-Von/Bis, Schwierigkeits-Chips
- Listenansicht mit `RideCard` Komponenten
- Tab-Wechsel: "In der Naehe" vs "Meine Rides"
- Floating Action Button (FAB) zum Erstellen

**`/community/create` (Ride erstellen):**
- Formular mit: Titel, Beschreibung, Datum/Uhrzeit, Treffpunkt (manuell oder aus Tour), Schwierigkeit, Max. Teilnehmer, Sichtbarkeits-Radius
- Optional: Tour verlinken (Tour-Suche einbetten)
- Submit: POST /community/rides

**`/community/{id}` (Ride-Detail):**
- Ride-Info-Card (Datum, Ort, Distanz, Hoehenmeter, Schwierigkeit)
- Teilnehmerliste (Name + Avatar, Status-Badge)
- Aktionen: "Anfrage senden" (Nicht-Creator), "Bestaetigen/Ablehnen" (Creator), "Absagen" (Creator)
- Wenn Tour verlinkt: Link zur Tour-Detailseite

### 5d. Neue Komponenten

| Datei | Beschreibung |
|-------|-------------|
| `webapp/src/components/RideCard.tsx` | Karte fuer Community Ride (aehnlich TourCard) |
| `webapp/src/components/ParticipantList.tsx` | Teilnehmerliste mit Status-Badges |
| `webapp/src/components/InviteModal.tsx` | Modal fuer Strava-Invite-Link-Generierung |

**`RideCard.tsx`** folgt dem Muster von `TourCard.tsx`:
- Titel, Creator-Name + Avatar, Datum + Uhrzeit
- Schwierigkeits-Badge, Distanz, Hoehenmeter
- Teilnehmerzaehler (z.B. "3/8 Fahrer")
- Status-Badge (offen/voll/abgesagt)

### 5e. Navigation Erweiterung

**Datei:** `/home/admin/projects/mtb-mcp/webapp/src/components/BottomNav.tsx`

"Community" als neuen Eintrag in `moreItems` hinzufuegen:
```typescript
const moreItems = [
  { href: "/community", icon: "👥", label: "Community" },  // NEU
  { href: "/bike", icon: "🔧", label: "Bike" },
  // ... bestehendes
];
```

---

## 6. Implementierungs-Reihenfolge und Abhaengigkeiten

### Phase A: Foundation (kann parallel)

| Schritt | Beschreibung | Abhaengigkeit |
|---------|-------------|---------------|
| A1 | Migrationen 16-20 in `migrations.py` | Keine |
| A2 | Pydantic Models in `models/community.py` | Keine |
| A3 | `StravaClient` um Clubs/Members/Gear/Paginierung erweitern | Keine |

### Phase B: Storage Layer (nach Phase A)

| Schritt | Beschreibung | Abhaengigkeit |
|---------|-------------|---------------|
| B1 | `CommunityStore` implementieren | A1, A2 |
| B2 | `StravaImportStore` implementieren | A1 |

### Phase C: Service Layer (nach Phase B)

| Schritt | Beschreibung | Abhaengigkeit |
|---------|-------------|---------------|
| C1 | `StravaImportService` implementieren | B2, A3 |
| C2 | Import-Trigger in Strava OAuth Callback einbauen | C1 |

### Phase D: API Layer (nach Phase B und teilweise C)

| Schritt | Beschreibung | Abhaengigkeit |
|---------|-------------|---------------|
| D1 | Community Rides Router (`routes/community.py`) | B1 |
| D2 | Router in `main.py` registrieren | D1 |
| D3 | Strava Import Endpoints in Auth-Router | C1 |

### Phase E: Frontend (nach Phase D)

| Schritt | Beschreibung | Abhaengigkeit |
|---------|-------------|---------------|
| E1 | TypeScript Types + API Client | D1, D3 |
| E2 | `RideCard`, `ParticipantList`, `InviteModal` Komponenten | E1 |
| E3 | `/community` Seite (Ride-Liste) | E2 |
| E4 | `/community/create` Seite | E2 |
| E5 | `/community/[id]` Seite (Detail) | E2 |
| E6 | BottomNav Update | E3 |

### Phase F: Tests (parallel zu E)

| Schritt | Beschreibung | Abhaengigkeit |
|---------|-------------|---------------|
| F1 | Unit Tests fuer `CommunityStore` (pytest + aiosqlite :memory:) | B1 |
| F2 | Unit Tests fuer `StravaImportService` (pytest + respx Mocking) | C1 |
| F3 | API Integration Tests (httpx ASGI Transport) | D1, D3 |
| F4 | E2E Tests (Playwright route interception) | E3-E5 |

### Parallelisierbarkeit

**Parallel ausfuehrbar:**
- Phase A (alle 3 Schritte gleichzeitig)
- Sub-Feature 1 (Community Rides: A1+A2 -> B1 -> D1 -> E1-E6) und Sub-Feature 3 (Strava Import: A1+A3 -> B2 -> C1 -> D3) koennen auf separaten Branches parallel entwickelt werden
- Tests (Phase F) parallel zur Frontend-Entwicklung
- `RideCard`, `ParticipantList`, `InviteModal` Komponenten parallel

**Sequentiell notwendig:**
- Migration muss vor Storage, Storage vor API, API vor Frontend
- Strava Import Service benoetigt sowohl StravaImportStore als auch StravaClient-Erweiterung
- OAuth Callback Trigger benoetigt fertigen Import Service

---

## 7. Privacy-Ueberlegungen

- Community Rides zeigen nur `display_name` und `avatar_url` von Teilnehmern
- `home_lat`/`home_lon` wird NIEMALS an andere User exponiert
- Creator-Email ist nicht sichtbar
- Strava Clubs/Members-Daten werden nicht persistiert (nur live abgefragt)
- Referral-Links tracken keine Email-Adressen, nur uses_count

---

## 8. Risiken und offene Fragen

1. **Strava API Rate Limits**: GET /athlete/clubs und GET /clubs/{id}/members verbrauchen vom 200 req/15min Budget. Der Import (200 Activities) braucht mindestens 1-2 Requests. Empfehlung: Import asynchron mit Backoff.

2. **Strava API TOS**: Strava verbietet das Speichern von Daten anderer Athleten. Club-Member-Infos duerfen nur angezeigt, nicht persistiert werden. Eigene Aktivitaeten duerfen gespeichert werden.

3. **Geo-Suche Performance**: Bei vielen Rides koennte die Bounding-Box-Abfrage langsam werden. Fuer die naechste Iteration: R-Tree Index oder Spatial Extension.

4. **Async Import**: Der Strava-Import nach Signup sollte async laufen (nicht die Callback-Response blockieren). Option A: Python `asyncio.create_task()` im gleichen Prozess. Option B: Background Worker Queue. Empfehlung fuer MVP: Option A mit `asyncio.create_task()`.

5. **Fitness-Berechnung ohne Powermeter**: Viele Fahrer haben keinen Powermeter. TSS kann naeherungsweise ueber `(Duration_minutes * Intensity_Factor^2)` berechnet werden, wobei `Intensity_Factor` aus durchschnittlicher Herzfrequenz oder Sport-Type heuristisch abgeleitet wird.

---

## Critical Files for Implementation

- `/home/admin/projects/mtb-mcp/src/mtb_mcp/storage/migrations.py` - All 5 new migrations (tables for community_rides, ride_participants, referral_links, strava_activities, and users column additions)
- `/home/admin/projects/mtb-mcp/src/mtb_mcp/clients/strava.py` - Extend with get_athlete_clubs(), get_club_members(), get_athlete_gear(), get_activities_page() methods
- `/home/admin/projects/mtb-mcp/src/mtb_mcp/api/routes/auth.py` - Add strava-import-status and strava-import endpoints, trigger async import in strava_callback
- `/home/admin/projects/mtb-mcp/src/mtb_mcp/storage/user_store.py` - Pattern to follow for CommunityStore; also needs import_status field access methods
- `/home/admin/projects/mtb-mcp/webapp/src/app/tours/page.tsx` - Frontend pattern to follow for the community rides list page (search + filter + cards)
