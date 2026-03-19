# Feature Backlog — mtb-mcp

Ideen und geplante Erweiterungen, nach Bereich gruppiert.

---

## Routing

| # | Feature | Quelle | Priorität | Notizen |
|---|---------|--------|-----------|---------|
| R-1 | **ORS Isochrones** — "Wo komme ich in 1h hin?" | ORS API `/v2/isochrones/cycling-mountain` | Mittel | Visualisierung der erreichbaren Fläche ab Startpunkt. Sehr nützlich für Tour-Suche: "Zeig mir alles was ich in 2h erreichen kann." |
| R-2 | **ORS Matrix** — Distanzmatrix zwischen Punkten | ORS API `/v2/matrix/cycling-mountain` | Niedrig | Nützlich für Multi-Stop Planung (z.B. Bikeparks vergleichen, nächsten Trail finden). |
| R-3 | **ORS Elevation** — Höhendaten für Koordinaten | ORS API `/v2/elevation/point` und `/line` | Niedrig | Fallback wenn BRouter nicht läuft und wir trotzdem Höhenprofile brauchen. |
| R-4 | **Custom BRouter MTB-Profile** | BRouter Profil-Syntax | Niedrig | Eigene Profile für Enduro (bevorzugt Trails bergab), XC (bevorzugt flowige Singletrails), Gravel. |

## Intelligence

| # | Feature | Priorität | Notizen |
|---|---------|-----------|---------|
| I-1 | **Reifendruck-Empfehlung** | Mittel | Basierend auf Fahrergewicht + Trail-Oberfläche + Reifenbreite. TyreWiz-Daten als Referenz. |
| I-2 | **Suspension-Import** | Niedrig | CSV-Import von BYB/Motion Instruments Daten. Federwegs-Analyse pro Trail-Segment. |
| I-3 | **Cross-Ride Trend-Analyse** | Mittel | "Werde ich schneller/fitter?" — Segment-Zeiten über Wochen/Monate vergleichen. |
| I-4 | **Enhanced Post-Ride** | Mittel | Segment-by-Segment Vergleich mit vorherigen Fahrten, nicht nur PRs. |

## Devices & Fitness-Plattformen

Empfohlener Datenfluss: `Huawei Watch → Huawei Health → Strava (auto-sync) → Intervals.icu (auto-sync)`

Indirekt abgedeckt via Strava + Intervals.icu (kein eigenes Server-API):
Apple Watch, Samsung Galaxy Watch, Google/Pixel Watch, alle Android Health Connect Geräte

Vollständige Analyse: [docs/DEVICE_INTEGRATION_RESEARCH.md](DEVICE_INTEGRATION_RESEARCH.md)

| # | Feature | API-Qualität | Priorität | Notizen |
|---|---------|-------------|-----------|---------|
| D-1 | **Intervals.icu Integration** | REST, API-Key, Swagger Docs | **Hoch** | Aggregiert Daten von Garmin/Polar/Suunto/COROS/Wahoo/Strava. Free Tier: CTL/ATL/TSB, Activities, Power Curves. Supporter ($4/Mo): volle Strava-History, Wetter-Analyse, Route Matching. Gestufter Ansatz: Free-Features immer nutzen, Supporter-Features wenn verfügbar. Ersetzt unsere manuelle CTL/ATL/TSB Berechnung. Siehe D-1a/D-1b. |
| D-1a | **Intervals.icu Free-Tier Client** | REST, Basic Auth (API_KEY) | **Hoch** | `clients/intervals.py`: Activities, Fitness (CTL/ATL/TSB), Power Curves, Intervall-Erkennung. Config: `MTB_MCP_INTERVALS_API_KEY`. Fallback auf eigene Berechnung wenn kein Key konfiguriert. |
| D-1b | **Intervals.icu Supporter-Features** | wie D-1a | Mittel | Volle Strava-History für Langzeit-Trends, Wetter-Integration, Route Matching (Auto-Commute Filter). Config: `MTB_MCP_INTERVALS_SUPPORTER=true`. Erkennung ob Supporter aktiv, graceful degradation auf Free-Features. |
| D-2 | **Huawei Health Kit** | REST, OAuth 2.0 | **Hoch** | User nutzt Huawei Watch. HR, GPS-Tracks, Schlaf, HRV, Stress. Braucht Huawei Developer Account. |
| D-3 | **Garmin Connect** | REST, OAuth 1.0a | Mittel | Größter MTB-Marktanteil. Grit/Flow/Jump-Metriken, Training Load, Body Battery, Route-Push via Courses API. Braucht Business Developer Approval. |
| D-4 | **Polar AccessLink** | REST, OAuth 2.0 | Niedrig | Freie offene API, einfach zu integrieren. Training Load, Recovery. |
| D-5 | **Suunto App** | REST, OAuth 2.0 | Niedrig | Ähnlich Polar, gute Outdoor-Daten. |
| D-6 | **COROS** | REST, API-Key | Niedrig | Wachsender Marktanteil bei Trail/Ultra. |

## API-Integrationen

| # | Feature | Priorität | Notizen |
|---|---------|-----------|---------|
| A-1 | **Trailforks API** | Hoch | Warten auf API-Zugang. Trail-Status (offen/gesperrt), Community-Reports. |
| A-2 | **Bosch eBike Cloud** | Mittel | Developer Program Enrollment nötig. Akku-Status live, Fahrhistorie, Motor-Diagnostik. |
| A-3 | **Wahoo Fitness** | Niedrig | OAuth2 Integration für Workout-Sync (Alternative zu Strava für manche Nutzer). |

## UX / Tools

| # | Feature | Priorität | Notizen |
|---|---------|-----------|---------|
| U-1 | **GPX Viewer/Zusammenfassung** | Mittel | Beliebige GPX-Datei analysieren: Distanz, Höhe, geschätzte Dauer, Trail-Matching. |
| U-2 | **Scheduled Notifications** | Mittel | Freitag-Abend automatisch Weekend-Empfehlung. Montag-Morgen Wochen-Summary. |
| U-3 | **Multi-Bike Strava Sync** | Niedrig | Strava gear_id automatisch mit Bike Garage matchen, Rides auto-loggen. |

---

*Neue Ideen hier eintragen. Priorisierung: Hoch / Mittel / Niedrig.*
