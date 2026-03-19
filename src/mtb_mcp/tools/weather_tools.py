"""MCP tools for weather data."""

from __future__ import annotations

from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.config import get_settings
from mtb_mcp.server import mcp


def _resolve_location(
    lat: float | None, lon: float | None
) -> tuple[float, float]:
    """Resolve lat/lon, falling back to home location from settings."""
    if lat is not None and lon is not None:
        return lat, lon
    settings = get_settings()
    return settings.home_lat, settings.home_lon


@mcp.tool()
async def weather_forecast(
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    """Get multi-day weather forecast for MTB riding.

    Provide lat/lon coordinates or leave empty for home location.
    Returns hourly temperature, wind, precipitation for the next days.
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    async with DWDClient() as client:
        forecast = await client.get_forecast(resolved_lat, resolved_lon)

    lines = [
        f"Weather Forecast for {forecast.location_name} "
        f"({forecast.lat:.2f}, {forecast.lon:.2f})",
        f"Generated: {forecast.generated_at:%Y-%m-%d %H:%M} UTC",
        "",
    ]

    current_date = ""
    for hour in forecast.hours:
        date_str = hour.time.strftime("%Y-%m-%d")
        if date_str != current_date:
            current_date = date_str
            lines.append(f"--- {date_str} ---")

        lines.append(
            f"  {hour.time:%H:%M}  "
            f"{hour.temp_c:5.1f}°C  "
            f"{hour.wind_speed_kmh:4.0f} km/h wind  "
            f"{hour.precipitation_mm:4.1f}mm  "
            f"{hour.condition.value}"
        )

    return "\n".join(lines)


@mcp.tool()
async def weather_rain_radar(
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    """Check rain radar nowcasting -- will it rain in the next 2 hours?

    Critical for deciding whether to start a ride or seek shelter.
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    async with DWDClient() as client:
        radar = await client.get_rain_radar(resolved_lat, resolved_lon)

    lines = [
        f"Rain Radar for ({radar.lat:.2f}, {radar.lon:.2f})",
        "",
    ]

    if radar.rain_approaching:
        if radar.eta_minutes == 0:
            lines.append("STATUS: It is currently raining!")
        else:
            lines.append(
                f"STATUS: Rain approaching in ~{radar.eta_minutes} minutes"
            )
    else:
        lines.append("STATUS: No rain expected in the next 60 minutes")

    lines.append("")
    lines.append("Next 60 minutes (5-min intervals, mm):")

    for i, mm in enumerate(radar.rain_next_60min):
        minute = i * 5
        bar = "#" * int(mm * 10)
        lines.append(f"  +{minute:2d}min: {mm:4.1f}mm {bar}")

    total = sum(radar.rain_next_60min)
    lines.append(f"\nTotal expected: {total:.1f}mm")

    return "\n".join(lines)


@mcp.tool()
async def weather_alerts(
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    """Check for active severe weather alerts (thunderstorms, heavy rain, etc).

    Always check before heading out on a ride.
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    async with DWDClient() as client:
        alerts = await client.get_alerts(resolved_lat, resolved_lon)

    if not alerts:
        return (
            f"No active weather alerts for ({resolved_lat:.2f}, {resolved_lon:.2f}). "
            "Conditions look safe!"
        )

    lines = [
        f"Active Weather Alerts for ({resolved_lat:.2f}, {resolved_lon:.2f})",
        f"Found {len(alerts)} alert(s):",
        "",
    ]

    for i, alert in enumerate(alerts, 1):
        lines.extend([
            f"[{i}] {alert.event} ({alert.severity.upper()})",
            f"    {alert.headline}",
            f"    From: {alert.onset:%Y-%m-%d %H:%M} UTC",
            f"    Until: {alert.expires:%Y-%m-%d %H:%M} UTC",
            f"    {alert.description[:200]}",
            "",
        ])

    return "\n".join(lines)


@mcp.tool()
async def weather_history(
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    """Get precipitation history for the last 48 hours.

    Important for estimating trail conditions -- recent rain means muddy trails.
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    async with DWDClient() as client:
        history = await client.get_rain_history(resolved_lat, resolved_lon)

    lines = [
        f"Precipitation History for ({history.lat:.2f}, {history.lon:.2f})",
        f"Last 48 hours total: {history.total_mm_48h:.1f}mm",
        "",
    ]

    if history.last_rain_hours_ago is not None:
        lines.append(
            f"Last significant rain (>0.5mm/h): {history.last_rain_hours_ago:.0f} hours ago"
        )
    else:
        lines.append("No significant rain in the last 48 hours")

    lines.append("")

    # Trail condition estimate
    if history.total_mm_48h < 2.0:
        lines.append("Trail estimate: DRY -- great riding conditions!")
    elif history.total_mm_48h < 10.0:
        if history.last_rain_hours_ago is not None and history.last_rain_hours_ago > 12:
            lines.append("Trail estimate: DAMP -- mostly rideable, some wet spots possible")
        else:
            lines.append("Trail estimate: WET -- expect slippery roots and rocks")
    else:
        lines.append("Trail estimate: MUDDY -- consider road/gravel alternatives")

    # Show summary of recent hours
    lines.append("")
    lines.append("Hourly precipitation (last 24h, newest first):")
    for i, mm in enumerate(history.hourly_mm[:24]):
        bar = "#" * int(mm * 5)
        lines.append(f"  -{i:2d}h: {mm:4.1f}mm {bar}")

    return "\n".join(lines)
