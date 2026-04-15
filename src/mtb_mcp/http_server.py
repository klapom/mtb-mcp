"""HTTP wrapper exposing mtb-mcp FastMCP tools as plain REST endpoints.

Runs on port 8205 by default. Each MCP tool is auto-exposed as:
    POST /tools/<tool_name>   body = JSON kwargs
    GET  /tools                → list of tool names + schemas
    GET  /healthz              → {"status": "ok"}

This is intentionally separate from the existing `api.main:app` (TrailPilot
REST API, port-independent) so external agents can invoke raw MCP tools
without speaking MCP/JSON-RPC.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="mtb-mcp HTTP wrapper",
    description="Plain-HTTP wrapper around mtb-mcp FastMCP tools (Strava, Komoot, MTB trails, weather, routing, bike garage).",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize_tool_result(result: Any) -> dict[str, Any]:
    """Normalize FastMCP tool-call result into plain JSON."""
    # FastMCP returns (content_blocks, structured_dict)
    structured: Any = None
    text_blocks: list[str] = []
    if isinstance(result, tuple) and len(result) == 2:
        content, structured = result
    else:
        content = result
    try:
        for block in content or []:
            text = getattr(block, "text", None)
            if text is not None:
                text_blocks.append(text)
    except TypeError:
        pass
    return {
        "text": "\n".join(text_blocks) if text_blocks else None,
        "structured": structured,
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "mtb-mcp-http"}


@app.get("/tools")
async def list_tools() -> dict[str, Any]:
    tools = await mcp.list_tools()
    return {
        "count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": (t.description or "").strip().split("\n", 1)[0],
                "input_schema": t.inputSchema,
            }
            for t in tools
        ],
    }


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request) -> dict[str, Any]:
    try:
        body = await request.json() if await request.body() else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object of tool arguments.")

    tools = await mcp.list_tools()
    if tool_name not in {t.name for t in tools}:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

    try:
        result = await mcp.call_tool(tool_name, body)
    except Exception as e:
        logger.exception("tool_call_failed", tool=tool_name)
        raise HTTPException(status_code=500, detail=f"Tool '{tool_name}' failed: {e}") from e

    return {"tool": tool_name, "result": _serialize_tool_result(result)}


def main() -> None:
    port = int(os.environ.get("MTB_MCP_HTTP_PORT", "8205"))
    host = os.environ.get("MTB_MCP_HTTP_HOST", "0.0.0.0")
    uvicorn.run(
        "mtb_mcp.http_server:app",
        host=host,
        port=port,
        log_level=os.environ.get("MTB_MCP_HTTP_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
