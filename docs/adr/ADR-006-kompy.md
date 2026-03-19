# ADR-006: kompy Wrapper für Komoot

## Status
Accepted

## Context
Komoot hat kein offizielles API. Die Reverse-Engineered v007 API ist stabil und weit verbreitet.

## Decision
`kompy` Python-Package als Wrapper für Komoot v007 API.

## Consequences

**Positiv:**
- Auth-Handling (Basic Auth → Token) bereits implementiert
- Pagination und HAL+JSON Parsing inklusive
- Tour-Suche, Details, GPX-Download getestet
- Aktiv maintained auf GitHub

**Negativ:**
- Abhängigkeit von inoffizieller API (kann brechen)
- kompy Package evtl. nicht vollständig (müssen wir ggf. erweitern)
- Keine Garantie für API-Stabilität
