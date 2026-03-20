"""FastAPI application — TrailPilot REST API."""

from __future__ import annotations

import time

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mtb_mcp.api.models import err

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="TrailPilot API",
    description="MTB Copilot — REST API for weather, trails, tours, routing, intelligence, and more.",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

# CORS — allow webapp on any localhost port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Add request timing to all responses."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Duration-Ms"] = str(duration_ms)
    return response


# ── Exception handlers ──────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — return structured error."""
    logger.error("unhandled_exception", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content=err("INTERNAL_ERROR", f"Internal server error: {type(exc).__name__}"),
    )


# ── Health check ────────────────────────────────────────────────────


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "trailpilot"}


# ── Register route modules ──────────────────────────────────────────

from mtb_mcp.api.routes import (  # noqa: E402
    bikes,
    dashboard,
    ebike,
    intelligence,
    routing,
    safety,
    strava,
    system,
    tours,
    trails,
    training,
    weather,
)

app.include_router(weather.router, prefix="/api/v1/weather", tags=["weather"])
app.include_router(trails.router, prefix="/api/v1/trails", tags=["trails"])
app.include_router(tours.router, prefix="/api/v1/tours", tags=["tours"])
app.include_router(routing.router, prefix="/api/v1/routing", tags=["routing"])
app.include_router(intelligence.router, prefix="/api/v1/intelligence", tags=["intelligence"])
app.include_router(strava.router, prefix="/api/v1/strava", tags=["strava"])
app.include_router(bikes.router, prefix="/api/v1/bikes", tags=["bikes"])
app.include_router(training.router, prefix="/api/v1/training", tags=["training"])
app.include_router(ebike.router, prefix="/api/v1/ebike", tags=["ebike"])
app.include_router(safety.router, prefix="/api/v1/safety", tags=["safety"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
