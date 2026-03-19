# ADR-001: Python statt TypeScript

## Status
Accepted

## Context
Das Projekt wurde initial als TypeScript MCP-Server aufgesetzt. Mehrere Kernabhängigkeiten existieren jedoch nur als Python-Packages.

## Decision
Python als Implementierungssprache.

## Consequences

**Positiv:**
- BLE Integration via `bleak` (kein Node.js Äquivalent mit gleicher Stabilität)
- `kompy` für Komoot v007 API bereits fertig
- Konsistenz mit AEGISRAG-Ökosystem (Poetry, Ruff, MyPy, pytest)
- email-classifier-mcp + servicenow-mcp beweisen Python-Kompatibilität mit mcporter

**Negativ:**
- TypeScript hat bessere MCP SDK Unterstützung (mehr Beispiele)
- Kein `@modelcontextprotocol/sdk` — stattdessen `mcp[cli]` Python Package
