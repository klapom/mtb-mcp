"""FastMCP Server for mtb-mcp — the TrailPilot MTB Copilot."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mtb-mcp")

# Tool imports are added per sprint (must come after mcp is defined):
from mtb_mcp.tools import (  # noqa: E402, F401
    ebike_tools,
    fitness_tools,
    intelligence_tools,
    maintenance_tools,
    routing_tools,
    safety_tools,
    sensor_tools,
    strava_tools,
    tour_search_tools,
    trail_tools,
    weather_tools,
)
