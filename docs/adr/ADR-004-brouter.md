# ADR-004: Self-Hosted BRouter

## Status
Accepted

## Context
Routing-Optionen für MTB: ORS (cycling-mountain), BRouter (MTB-Profile), OSRM (kein MTB).

## Decision
Self-Hosted BRouter via Docker, ORS als Fallback.

## Consequences

**Positiv:**
- Echte MTB-optimierte Routenberechnung mit dedizierten Profilen
- Volle Kontrolle über Routing-Profile (anpassbar)
- Keine Rate Limits (self-hosted)
- Bereits als Docker Image verfügbar

**Negativ:**
- Zusätzlicher Docker-Container
- Segment-Daten Download nötig (~500MB für Deutschland)
- Wartungsaufwand für Updates
