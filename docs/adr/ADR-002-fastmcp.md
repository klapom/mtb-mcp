# ADR-002: FastMCP statt Low-Level Server

## Status
Accepted

## Context
Die Python MCP SDK bietet zwei Wege: Low-Level `Server` Klasse oder High-Level `FastMCP` Wrapper.

## Decision
FastMCP verwenden.

## Consequences

**Positiv:**
- Saubere Tool-Definition via `@mcp.tool()` Decorator
- 1-Line Transport: `mcp.run(transport="stdio")`
- Automatische Parameter-Validierung
- email-classifier-mcp als bewährte Referenz

**Negativ:**
- Weniger Kontrolle über Low-Level MCP-Protokoll
- Abhängigkeit von FastMCP API-Stabilität
