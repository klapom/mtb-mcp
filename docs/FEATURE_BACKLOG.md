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

## Mobile App (Phase 4)

### Framework-Entscheidung

| Option | Vorteil | Nachteil | Empfehlung |
|--------|---------|----------|------------|
| **React Native** | 1 Codebase → Android + iOS, große Community, react-native-ble-plx für BLE | Bridge-Overhead für BLE-intensive Features | **Empfohlen** |
| **Flutter** | 1 Codebase, flutter_blue für BLE, gute Performance | Dart-Ökosystem kleiner | Alternative |
| **Kotlin (Android nativ)** | Beste Health Connect Integration, volle HMS-Unterstützung | Nur Android | Für Android-First |
| **Swift/SwiftUI (iOS nativ)** | Beste HealthKit Integration, Core Bluetooth nativ | Nur iOS | Für iOS-First |

### Health Data Integration

| # | Feature | Plattform | Priorität | Notizen |
|---|---------|-----------|-----------|---------|
| M-1 | **Android Health Connect** | Android | **Hoch** | Zentraler Hub für Samsung, Pixel Watch, Garmin, Fitbit, Oura, Withings. 50+ Datentypen: HR, HRV, GPS-Routen, Sleep, SpO2, VO2max, Workouts. Nur 30 Tage lokal. Braucht `READ_EXERCISE_ROUTES` Permission mit per-Route User-Dialog. |
| M-2 | **iOS HealthKit** | iOS | **Hoch** | Apple Watch Daten mit voller Fidelity: HR (5s), HRV, VO2max, GPS-Routen (HKWorkoutRoute), Sleep Stages. Nicht-Apple Watches: nur Teilmenge, **keine GPS-Routen**. Lokaler Datenspeicher, kein Cloud-API. |
| M-3 | **Huawei Health Kit (HMS)** | Android (Huawei) | **Hoch** | Einziger Weg für direkte Huawei Watch Daten. HR, GPS, Sleep, HRV, Stress, SpO2, ECG. Braucht HMS Core (nur Huawei-Phones nativ, Sideload auf anderen Android unzuverlässig). Huawei Developer Console Registration nötig. |
| M-4 | **Health Sync Bridge** | Android | **Hoch** | Bridge-App (€2.99) für Huawei → Health Connect Sync. Workaround wenn kein Huawei-Phone: Huawei Health → Health Sync → Health Connect → TrailPilot. Auch nützlich für Samsung Health → Health Connect. |
| M-5 | **Samsung Health Data SDK** | Android | Mittel | Direktzugriff auf Galaxy Watch Daten ohne Health Connect Umweg. Kein Partner-Approval nötig (Dev Mode). HR, GPS, Sleep, Workouts. Galaxy Watch 4+ (Wear OS). Altes Samsung Health SDK deprecated Juli 2025. |
| M-6 | **Wear OS Health Services** | Android (Wear OS) | Mittel | Direkter Sensor-Zugriff auf Wear OS Watches (Pixel Watch, Galaxy Watch 4+). ExerciseClient für Echtzeit-HR (1Hz), GPS, Elevation. PassiveMonitoringClient für Hintergrund-Tracking. Braucht Watch-App + Phone-Companion. |
| M-7 | **Garmin via Health Connect** | Android | Mittel | Seit Juli 2025 supported. Steps, Sleep, Workouts, HR. Einweg (Garmin → Health Connect). Proprietäre Metriken (Body Battery, Training Load, HRV Status) NICHT included. |

### BLE Sensor Integration (nativ, beide Plattformen)

| # | Feature | Plattform | Priorität | Notizen |
|---|---------|-----------|-----------|---------|
| M-8 | **BLE HR-Gurt direkt** | Android + iOS | **Hoch** | Standard BLE Heart Rate Service (0x180D). Polar H10, Garmin HRM-Pro, Wahoo TICKR — live HR + RR-Intervalle ohne Companion-App. Android: BLE API. iOS: Core Bluetooth. |
| M-9 | **BLE Power Meter** | Android + iOS | **Hoch** | Cycling Power Service (0x1818). Stages, Favero Assioma, Quarq, 4iiii — live Watt, Kadenz, Pedal-Balance. Direkt per BLE, kein Cloud-Umweg. |
| M-10 | **BLE Speed/Cadence** | Android + iOS | Mittel | Cycling Speed & Cadence Service (0x1816). Wahoo, Garmin, Magene Sensoren. Wheel/Crank Revolutions für Speed + Kadenz. |
| M-11 | **BLE TyreWiz/ShockWiz** | Android + iOS | Mittel | Quarq TyreWiz (Reifendruck live) + ShockWiz (Federwegs-Analyse). Proprietäres GATT-Protokoll, bereits in `ble/tyrewiz.py` + `ble/shockwiz.py` implementiert. |
| M-12 | **Watch als HR-Broadcast** | Android + iOS | Niedrig | Manche Watches können HR als Standard-BLE-Service broadcasten (Garmin "Broadcast Heart Rate" Modus, Apple Watch via HeartCast). Watch wird quasi zum HR-Gurt. Opt-in, nur HR. |

### Mobile-spezifische API Endpoints

| # | Feature | Priorität | Notizen |
|---|---------|-----------|---------|
| M-13 | **`POST /api/v1/health/sync`** | **Hoch** | Phone pusht Health Connect / HealthKit Daten zum TrailPilot Server. Batch-Upload: Workouts, HR-Samples, Sleep, GPS-Routen. Idempotent (kein Duplikat bei Re-Sync). Delta-Sync über `last_sync_timestamp`. |
| M-14 | **`POST /api/v1/tracking/live`** | **Hoch** | Live GPS + HR Streaming während der Fahrt. WebSocket oder HTTP Polling (5s Intervall). Für Echtzeit-Tracking, Notfall-Erkennung, Live-Ride-Score. |
| M-15 | **`POST /api/v1/devices`** | Mittel | Device Registration: Phone-Modell, OS-Version, Watch-Typ, verbundene BLE-Sensoren. Für Push-Notifications und Feature-Gating (z.B. BLE nur wenn Phone unterstützt). |
| M-16 | **`POST /api/v1/safety/crash-report`** | Mittel | Crash Detection via Phone Accelerometer. Automatischer Alert an Notfallkontakt wenn keine Bewegung + kein Entwarnung nach 60s. Braucht `POST /api/v1/notifications/push` für FCM/APNs. |
| M-17 | **`POST /api/v1/notifications/push`** | Mittel | Push-Notification Registration (FCM Token für Android, APNs Token für iOS). Für: Weekend-Empfehlung Freitag Abend, Wartungs-Reminder, Safety Timer Alerts, Wetter-Warnungen. |
| M-18 | **Offline Sync** | Mittel | Lokale SQLite auf Phone für Offline-Rides. Sync-Queue: Rides werden lokal gespeichert, bei Connectivity zum Server gepusht. Conflict Resolution: Server wins (außer GPS-Daten, da Phone wins). |

### Plattform-Kompatibilitätsmatrix

| Datenquelle | Android (Health Connect) | Android (HMS/Huawei) | iOS (HealthKit) | iOS (Core BT) |
|-------------|------------------------|---------------------|-----------------|---------------|
| HR live (Workout) | Ja | Ja | Ja (Apple Watch) | Ja (BLE Gurt) |
| HR kontinuierlich | Ja | Ja | Ja (Apple Watch) | Nein |
| HRV | Ja | Ja | Ja (Apple Watch) | Nein |
| GPS-Routen | Ja | Ja | **Nur Apple Watch** | Nein |
| Sleep Stages | Ja | Ja | Ja (Apple Watch) | Nein |
| SpO2 | Ja | Ja | Ja (Apple Watch) | Nein |
| VO2max | Ja | Nein | Ja (Apple Watch) | Nein |
| Power (Watt) | Ja | Nein | Nein | Ja (BLE PM) |
| Reifendruck | Nein | Nein | Nein | Ja (TyreWiz) |

## UX / Tools

| # | Feature | Priorität | Notizen |
|---|---------|-----------|---------|
| U-1 | **GPX Viewer/Zusammenfassung** | Mittel | Beliebige GPX-Datei analysieren: Distanz, Höhe, geschätzte Dauer, Trail-Matching. |
| U-2 | **Scheduled Notifications** | Mittel | Freitag-Abend automatisch Weekend-Empfehlung. Montag-Morgen Wochen-Summary. |
| U-3 | **Multi-Bike Strava Sync** | Niedrig | Strava gear_id automatisch mit Bike Garage matchen, Rides auto-loggen. |

---

*Neue Ideen hier eintragen. Priorisierung: Hoch / Mittel / Niedrig.*
