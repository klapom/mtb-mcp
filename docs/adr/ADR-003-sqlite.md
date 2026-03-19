# ADR-003: SQLite für lokale Daten

## Status
Accepted

## Context
Bike-Garage, API-Response Cache und Tour-History brauchen Persistenz. Eine Netzwerk-Datenbank wäre Overkill.

## Decision
SQLite via `aiosqlite` unter `~/.mtb-mcp/mtb.db`.

## Consequences

**Positiv:**
- Zero-Infrastruktur (keine Docker-DB nötig)
- Async-kompatibel via aiosqlite
- Einfaches Backup (eine Datei kopieren)
- Perfekt für Single-User Szenario

**Negativ:**
- Kein concurrent write access (irrelevant für Single-User)
- Kein Full-Text-Search ohne Extension (FTS5 verfügbar falls nötig)
