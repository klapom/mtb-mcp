# ADR-005: DWD statt OpenWeatherMap

## Status
Accepted

## Context
Wettervorhersage wird für Ride Score, Trail Condition und Wochenend-Planung benötigt.

## Decision
DWD OpenData als primäre Wetterdatenquelle.

## Consequences

**Positiv:**
- Komplett kostenlos, unbegrenzte Requests
- DACH-Fokus mit hoher Auflösung
- Regenradar Nowcasting alle 5 Minuten
- Unwetterwarnungen im CAP-Format
- Niederschlagshistorie für Trail Condition

**Negativ:**
- Nur DACH-Region (kein Problem für Franken/Alpen-Fokus)
- Komplexere API-Struktur als OpenWeatherMap
- Datenformat teilweise CSV/GRIB statt JSON
