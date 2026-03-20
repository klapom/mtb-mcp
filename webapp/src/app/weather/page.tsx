"use client";

import { useApi } from "@/hooks/useApi";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import type {
  WeatherForecast,
  RainRadar,
  WeatherAlert,
  RainHistory,
} from "@/lib/types";

/* ── Forecast Section ──────────────────────────────────────────── */

function ForecastSection() {
  const { data, error, isLoading, mutate } =
    useApi<WeatherForecast>("/weather/forecast");

  if (isLoading) return <LoadingState text="Vorhersage laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  return (
    <Card>
      <CardHeader title="Vorhersage" />
      <p className="text-sm text-text-secondary mb-3">{data.location_name}</p>
      <div className="overflow-x-auto flex gap-2 pb-2 -mx-1 px-1">
        {data.hours.map((h) => {
          const hour = new Date(h.time).toLocaleTimeString("de-DE", {
            hour: "2-digit",
            minute: "2-digit",
          });
          const rainPct = Math.min(h.precipitation_probability, 100);

          return (
            <div
              key={h.time}
              className="flex-none w-[72px] bg-white/4 rounded-lg p-2 text-center space-y-1"
            >
              <p className="text-[11px] text-text-muted">{hour}</p>
              <p className="text-sm font-bold">{Math.round(h.temp_c)}°</p>
              <p className="text-[10px] text-text-secondary">
                {h.wind_speed_kmh} km/h
              </p>
              {/* Rain probability mini bar */}
              <div className="w-full h-1 bg-white/8 rounded-full overflow-hidden mt-1">
                <div
                  className="h-full bg-accent-blue rounded-full"
                  style={{ width: `${rainPct}%` }}
                />
              </div>
              {h.precipitation_mm > 0 && (
                <p className="text-[10px] text-accent-blue">
                  {h.precipitation_mm} mm
                </p>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

/* ── Rain Radar Section ────────────────────────────────────────── */

function RainRadarSection() {
  const { data, error, isLoading, mutate } =
    useApi<RainRadar>("/weather/rain-radar");

  if (isLoading) return <LoadingState text="Regenradar laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  return (
    <Card>
      <CardHeader
        title="Regenradar"
        action={
          <Badge variant={data.approaching ? "red" : "green"}>
            {data.approaching ? "Regen naht" : "Kein Regen"}
          </Badge>
        }
      />
      <p className="text-sm text-text-primary">{data.summary}</p>
      {data.approaching && data.minutes_until_rain != null && (
        <p className="mt-2 text-xs text-accent-orange">
          Regen in ca. {data.minutes_until_rain} Minuten
          {data.intensity && ` (${data.intensity})`}
        </p>
      )}
    </Card>
  );
}

/* ── Alerts Section ────────────────────────────────────────────── */

function severityVariant(severity: string): string {
  switch (severity.toLowerCase()) {
    case "extreme":
    case "severe":
      return "red";
    case "moderate":
      return "orange";
    case "minor":
      return "blue";
    default:
      return "gray";
  }
}

function AlertsSection() {
  const { data, error, isLoading, mutate } =
    useApi<{ alerts: WeatherAlert[] }>("/weather/alerts");

  if (isLoading) return <LoadingState text="Warnungen laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  return (
    <Card>
      <CardHeader title="Wetterwarnungen" />
      {data.alerts.length === 0 ? (
        <p className="text-sm text-text-muted">Keine Warnungen</p>
      ) : (
        <div className="space-y-3">
          {data.alerts.map((alert, idx) => (
            <div key={idx} className="bg-white/4 rounded-lg p-3">
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="text-sm font-semibold">{alert.headline}</p>
                <Badge variant={severityVariant(alert.severity)}>
                  {alert.severity}
                </Badge>
              </div>
              <p className="text-xs text-text-secondary">{alert.description}</p>
              <div className="flex items-center gap-3 mt-2 text-[11px] text-text-muted">
                <span>{alert.region}</span>
                <span>
                  {new Date(alert.start).toLocaleDateString("de-DE", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                  {" - "}
                  {new Date(alert.end).toLocaleDateString("de-DE", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/* ── Rain History Section ──────────────────────────────────────── */

function RainHistorySection() {
  const { data, error, isLoading, mutate } =
    useApi<RainHistory>("/weather/history");

  if (isLoading) return <LoadingState text="Regenverlauf laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  // API may return hourly_mm (flat array) or hours (object array)
  const bars: number[] = data.hourly_mm ?? data.hours?.map((h) => h.precipitation_mm) ?? [];
  const totalMm = data.total_mm_48h ?? data.total_mm ?? 0;
  const maxPrecip = Math.max(...bars, 1);

  return (
    <Card>
      <CardHeader title="Regenverlauf (48h)" />
      <p className="text-sm text-text-primary mb-3">
        Gesamt:{" "}
        <span className="font-bold text-accent-blue">{totalMm} mm</span>
      </p>
      <div className="overflow-x-auto pb-2">
        <div className="flex items-end gap-[2px] h-20 min-w-max">
          {bars.map((mm, idx) => {
            const heightPct = (mm / maxPrecip) * 100;
            const showLabel = idx % 6 === 0;

            return (
              <div key={idx} className="flex flex-col items-center w-3">
                <div
                  className="w-full bg-accent-blue/60 rounded-t-sm transition-[height] duration-300"
                  style={{
                    height: `${Math.max(heightPct, mm > 0 ? 4 : 0)}%`,
                    minHeight: mm > 0 ? "2px" : "0px",
                  }}
                  title={`${mm} mm`}
                />
                {showLabel && (
                  <span className="text-[8px] text-text-muted mt-1">
                    {idx}h
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

/* ── Main Weather Page ─────────────────────────────────────────── */

export default function WeatherPage() {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold mb-3">Wetter</h2>
      <ForecastSection />
      <RainRadarSection />
      <AlertsSection />
      <RainHistorySection />
    </div>
  );
}
