"use client";

import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { RideScoreGauge } from "@/components/RideScoreGauge";
import { WeatherStrip } from "@/components/WeatherStrip";
import type { DashboardData } from "@/lib/types";

function SubScoreBar({ label, value }: { label: string; value: number }) {
  const color =
    value >= 80
      ? "bg-accent-green"
      : value >= 60
        ? "bg-accent-orange"
        : "bg-accent-red";

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-text-secondary w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-white/8 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-[width] duration-700 ${color}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs text-text-muted w-7 text-right">{value}</span>
    </div>
  );
}

function conditionVariant(condition: string): string {
  switch (condition.toLowerCase()) {
    case "dry":
      return "green";
    case "damp":
      return "blue";
    case "wet":
      return "orange";
    case "muddy":
      return "red";
    default:
      return "gray";
  }
}

function scoreVariant(score: number): string {
  if (score >= 80) return "green";
  if (score >= 60) return "orange";
  return "red";
}

const quickActions = [
  { href: "/weather", label: "Wetter", icon: "cloud-sun" },
  { href: "/trails", label: "Trails", icon: "mountain" },
  { href: "/tours", label: "Touren", icon: "map" },
  { href: "/bike", label: "Bike", icon: "wrench" },
] as const;

const actionIcons: Record<string, string> = {
  "cloud-sun": "\u2601",
  mountain: "\u26F0",
  map: "\uD83D\uDDFA",
  wrench: "\uD83D\uDD27",
};

export default function DashboardPage() {
  const { data, error, isLoading, mutate } = useApi<DashboardData>("/dashboard");

  if (isLoading) return <LoadingState text="Dashboard laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  const { ride_score, weather_current, trail_condition, weekend_preview, next_service, active_timer } = data;

  return (
    <div className="space-y-3">
      {/* ── Ride Score ──────────────────────────────────────────── */}
      <Card>
        <CardHeader title="Ride Score" />
        <RideScoreGauge score={ride_score.score} verdict={ride_score.verdict} />
        <div className="mt-4 space-y-2">
          <SubScoreBar label="Wetter" value={ride_score.weather_score} />
          <SubScoreBar label="Trail" value={ride_score.trail_score} />
          <SubScoreBar label="Wind" value={ride_score.wind_score} />
          <SubScoreBar label="Tageslicht" value={ride_score.daylight_score} />
        </div>
        {ride_score.factors && ride_score.factors.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {ride_score.factors.map((f) => (
              <Badge key={f} variant="red">{f}</Badge>
            ))}
          </div>
        )}
      </Card>

      {/* ── Weather ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader title="Aktuelles Wetter" />
        <WeatherStrip weather={weather_current} />
        <p className="mt-2 text-xs text-text-muted capitalize">{weather_current.condition}</p>
      </Card>

      {/* ── Trail Condition ─────────────────────────────────────── */}
      <Card>
        <CardHeader title="Trail Zustand" />
        <div className="flex items-center justify-between">
          <div>
            <Badge variant={conditionVariant(trail_condition.condition)}>
              {trail_condition.condition}
            </Badge>
            <p className="mt-2 text-xs text-text-secondary">
              Oberfläche: {trail_condition.surface}
            </p>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold text-accent-blue">
              {trail_condition.rain_48h_mm} <span className="text-xs font-normal">mm</span>
            </p>
            <p className="text-[11px] text-text-muted">Regen 48h</p>
          </div>
        </div>
        <p className="mt-2 text-[11px] text-text-muted">
          Konfidenz: {trail_condition.confidence}
        </p>
      </Card>

      {/* ── Weekend Preview ─────────────────────────────────────── */}
      <Card>
        <CardHeader title="Wochenend-Vorschau" />
        <div className="grid grid-cols-2 gap-3">
          {(["saturday", "sunday"] as const).map((day) => {
            const d = weekend_preview[day];
            return (
              <div
                key={day}
                className="bg-white/4 rounded-lg p-3 text-center"
              >
                <p className="text-xs text-text-secondary mb-1">
                  {day === "saturday" ? "Samstag" : "Sonntag"}
                </p>
                <p className="text-2xl font-bold">
                  <span className={`text-${scoreVariant(d.score)}`}>
                    {d.score}
                  </span>
                </p>
                {d.condition && (
                  <Badge variant={conditionVariant(d.condition)}>
                    {d.condition}
                  </Badge>
                )}
                {d.verdict && !d.condition && (
                  <Badge variant={scoreVariant(d.score)}>
                    {d.verdict}
                  </Badge>
                )}
                {d.temp_range && (
                  <p className="mt-1 text-xs text-text-muted">{d.temp_range}</p>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      {/* ── Next Service ────────────────────────────────────────── */}
      {next_service && (
        <Card>
          <CardHeader title="Nächster Service" />
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm font-semibold">{next_service.component_type}</p>
              <p className="text-xs text-text-secondary">{next_service.bike}</p>
            </div>
            <Badge
              variant={
                next_service.status === "good"
                  ? "green"
                  : next_service.status === "warning"
                    ? "orange"
                    : "red"
              }
            >
              {next_service.status}
            </Badge>
          </div>
          <ProgressBar pct={next_service.wear_pct} />
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-text-muted">
              Verschleiß {next_service.wear_pct}%
            </span>
            <span className="text-xs text-text-secondary">
              {next_service.km_remaining} km verbleibend
            </span>
          </div>
        </Card>
      )}

      {/* ── Active Timer ────────────────────────────────────────── */}
      {active_timer && active_timer.active && (
        <Card className="border-accent-orange/30">
          <CardHeader title="Aktiver Timer" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">{active_timer.ride_description}</p>
              <p className="text-xs text-text-secondary mt-1">
                Safety Timer aktiv
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-accent-orange">
                {active_timer.remaining_minutes}
              </p>
              <p className="text-[11px] text-text-muted">Min. verbleibend</p>
            </div>
          </div>
        </Card>
      )}

      {/* ── Quick Actions ───────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-2">
        {quickActions.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="flex flex-col items-center gap-1.5 bg-bg-card border border-border-card rounded-xl p-3 transition-colors hover:bg-bg-card-hover active:scale-95"
          >
            <span className="text-lg">{actionIcons[action.icon]}</span>
            <span className="text-[11px] text-text-secondary font-medium">
              {action.label}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
