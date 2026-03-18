# MTB MCP — Use Cases

## 1. Strava Activity Tracking

| Use Case | Tool | Beispiel |
|----------|------|---------|
| Letzte Fahrten anzeigen | `get_recent_activities` | "Zeig mir meine letzten 5 MTB-Fahrten" |
| Monats-/Jahresstatistik | `get_athlete_stats` | "Wie viele km bin ich diesen Monat gefahren?" |
| Fahrt-Details mit Splits | `get_activity_details` | "Wie war meine letzte Tour am Hetzlas?" |
| Höhenprofil & Herzfrequenz | `get_activity_streams` | "Zeig mir die Höhenmeter meiner letzten Fahrt" |
| Segment-Bestzeiten | `get_segment_leaderboard` | "Wie stehe ich im Vergleich auf dem S2-Trail?" |
| Segment-Entdeckung | `explore_segments` | "Welche Segmente gibt es rund um Neunkirchen?" |
| GPX-Export | `export_route_gpx` | "Exportiere meine Lieblingsroute als GPX" |
| Wöchentlicher Report | Scheduled Task | Automatischer Montag-Morgen-Bericht per WhatsApp |

## 2. Komoot Tour-Suche & Planung

| Use Case | Tool | Beispiel |
|----------|------|---------|
| Tour-Suche nach Region | `search_tours` | "Finde MTB-Touren bei Erlangen, 30-50km" |
| Tour nach Schwierigkeit | `search_tours` | "Leichte MTB-Tour in der Fränkischen Schweiz" |
| Tour-Details | `get_tour_details` | "Zeig mir Details zur Tour 12345" |
| GPX herunterladen | `download_tour_gpx` | "Lade die Tour als GPX für mein Garmin" |
| Tour per WhatsApp teilen | `download_tour_gpx` + `send_file` | "Schick mir die GPX-Datei" |

## 3. Trail-Informationen (OSM)

| Use Case | Tool | Beispiel |
|----------|------|---------|
| Trails in der Nähe | `find_trails` | "Welche Trails gibt es am Hetzlas?" |
| Schwierigkeitsfilter | `find_trails` | "Zeig mir S2+ Trails bei Erlangen" |
| Trail-Katalog Region | `find_trails` | "Alle MTB-Trails in 20km Umkreis" |

## 4. GPS-Tour.info Tour-Suche

| Use Case | Tool | Beispiel |
|----------|------|---------|
| Tour-Suche nach Region | `search_gpstour` | "Finde MTB-Touren auf gps-tour.info bei Erlangen" |
| Tour-Details abrufen | `get_gpstour_details` | "Zeig mir Details zur Tour 43168" |
| GPX herunterladen | `download_gpstour_gpx` | "Lade die SingleTrails Erlangen als GPX" |
| GPX per WhatsApp | `download_gpstour_gpx` + `send_file` | "Schick mir die GPX-Datei" |
| Beliebte Touren | `search_gpstour` + Downloads-Sortierung | "Was sind die beliebtesten MTB-Touren in der Fränkischen Schweiz?" |

## 5. Wetter-basierte Empfehlungen

| Use Case | Tool-Kombination | Beispiel |
|----------|-----------------|---------|
| Ride-or-not-Entscheidung | Weather + Trail-Daten | "Kann ich morgen biken?" |
| Wochenend-Planung | Forecast + Tour-Suche | "Welcher Tag ist besser, Samstag oder Sonntag?" |
| Proaktive Empfehlung | Scheduled: Forecast + Komoot | Freitag-Abend: "Samstag wird perfekt, 18°C, hier ist eine Tour..." |
| Regen-Warnung | DWD Radar + Tour-Dauer | "Regen kommt in 2h, Tour dauert 3h — lieber die kurze Variante" |

## 5. Routenplanung

| Use Case | Tool | Beispiel |
|----------|------|---------|
| MTB-Route berechnen | `plan_route` (BRouter) | "Plane eine Route von Neunkirchen zum Hetzlas" |
| Rundtour generieren | `plan_loop` | "30km Rundtour ab Forth, mittlere Schwierigkeit" |
| Route mit Wetter | Route + Forecast | "Plane die Tour und sag mir wie das Wetter wird" |

## 6. Kombinations-Szenarien

### "Perfektes Wochenende"
1. Freitag 18:00: Scheduled Task prüft Wetter für Sa/So
2. Wenn Bikewetter: Komoot-Tour passend zur Fitness suchen
3. WhatsApp-Nachricht: "Samstag wird top! Hier ist eine Tour am Hetzlas (42km, 850hm). GPX im Anhang."

### "Post-Ride Analyse"
1. Nach Strava-Upload: Letzte Aktivität abrufen
2. Segment-Zeiten vergleichen mit vorherigen Versuchen
3. "Du warst heute 12s schneller am S2-Anstieg! Neue Bestzeit."

### "Trail-Wetter-Check"
1. "Wie sind die Trails am Moritzberg?"
2. → OSM: Trail-Daten (S1-S2, Waldboden)
3. → Wetter: Letzte 48h Niederschlag prüfen
4. → "Gestern 15mm Regen, Waldboden-Trails wahrscheinlich matschig. Besser die Schotter-Variante über den Höhenweg."
