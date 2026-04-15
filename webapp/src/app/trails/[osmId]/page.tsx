"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { useCachedApi } from "@/hooks/useCachedApi";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ElevationProfile } from "@/components/ElevationProfile";
import { TrailCard } from "@/components/TrailCard";
import type { TrailDetail, Trail, WeatherForecast } from "@/lib/types";

const TrailMap = dynamic(
  () => import("@/components/TrailMap").then((m) => ({ default: m.TrailMap })),
  { ssr: false }
);

// --- Surface labels ---

const surfaceLabels: Record<string, string> = {
  dirt: "Erde",
  gravel: "Schotter",
  rock: "Fels",
  roots: "Wurzeln",
};

// --- Condition badge variant ---

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

// --- Weather condition icons ---

function weatherIcon(condition: string): string {
  const c = condition.toLowerCase();
  if (c.includes("sun") || c.includes("clear")) return "\u2600\uFE0F";
  if (c.includes("partly") || c.includes("cloud")) return "\u26C5";
  if (c.includes("rain") || c.includes("drizzle")) return "\uD83C\uDF27\uFE0F";
  if (c.includes("thunder") || c.includes("storm")) return "\u26C8\uFE0F";
  if (c.includes("snow")) return "\uD83C\uDF28\uFE0F";
  if (c.includes("fog") || c.includes("mist")) return "\uD83C\uDF2B\uFE0F";
  if (c.includes("overcast")) return "\u2601\uFE0F";
  return "\u2601\uFE0F";
}

// --- GPX builder ---

function buildGpx(
  name: string,
  geometry: { lat: number; lon: number; ele: number | null }[]
): string {
  const points = geometry
    .map(
      (p) =>
        `<trkpt lat="${p.lat}" lon="${p.lon}">${p.ele != null ? `<ele>${p.ele}</ele>` : ""}</trkpt>`
    )
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="TrailPilot">
<trk><name>${name}</name><trkseg>
${points}
</trkseg></trk></gpx>`;
}

function downloadGpx(name: string, geometry: { lat: number; lon: number; ele: number | null }[]) {
  const gpxContent = buildGpx(name, geometry);
  const blob = new Blob([gpxContent], { type: "application/gpx+xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${name.replace(/[^a-zA-Z0-9_-]/g, "_")}.gpx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// --- Elevation gain calculation ---

function calcElevationGain(geometry: { lat: number; lon: number; ele: number | null }[]): number {
  let gain = 0;
  const pts = geometry.filter((p) => p.ele != null);
  for (let i = 1; i < pts.length; i++) {
    const diff = pts[i].ele! - pts[i - 1].ele!;
    if (diff > 0) gain += diff;
  }
  return Math.round(gain);
}

// --- Page ---

export default function TrailDetailPage() {
  const { osmId } = useParams<{ osmId: string }>();
  const { user } = useAuth();
  const { data, error, isLoading, mutate } = useApi<TrailDetail>(
    osmId ? `/trails/${osmId}` : null
  );

  // Derive trail coordinates
  const trailLat = data?.lat ?? data?.geometry?.[0]?.lat ?? null;
  const trailLon = data?.lon ?? data?.geometry?.[0]?.lon ?? null;

  // Weather at trail location
  const { data: weather } = useApi<WeatherForecast>(
    trailLat != null && trailLon != null
      ? `/weather/forecast?lat=${trailLat}&lon=${trailLon}&hours=12`
      : null
  );

  // Similar trails nearby
  const { data: nearbyTrails } = useCachedApi<Trail[]>(
    trailLat != null && trailLon != null
      ? `/trails?radius_km=10&lat=${trailLat}&lon=${trailLon}`
      : null,
    60 * 60 * 1000
  );

  if (isLoading) return <LoadingState text="Trail laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  const scale = data.mtb_scale || data.difficulty || "";
  const surfaceLabel = surfaceLabels[data.surface] ?? data.surface;
  const elevGain =
    data.elevation_gain_m ?? (data.geometry ? calcElevationGain(data.geometry) : null);
  const hasGeometry = data.geometry && data.geometry.length >= 2;

  // Filter nearby trails: exclude current, take max 3
  const similarTrails = (nearbyTrails ?? [])
    .filter((t) => t.osm_id !== data.osm_id)
    .slice(0, 3);

  // Weather: take first 6 hours
  const weatherHours = (weather?.hours ?? []).slice(0, 6);

  return (
    <div className="space-y-4">
      {/* Back link */}
      <Link
        href="/trails"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary transition-colors"
      >
        &larr; Entdecken
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold flex-1">
          {data.name || `Trail ${data.osm_id}`}
        </h1>
        {scale && <Badge variant={scale.toLowerCase()}>{scale}</Badge>}
      </div>

      {/* Basic info */}
      <div className="flex gap-3 text-sm text-text-secondary">
        <span>{(data.length_m / 1000).toFixed(1)} km</span>
        <span>&middot;</span>
        <span>{surfaceLabel}</span>
        {elevGain != null && elevGain > 0 && (
          <>
            <span>&middot;</span>
            <span>&uarr; {elevGain} m</span>
          </>
        )}
      </div>

      {/* Map */}
      {hasGeometry && <TrailMap geometry={data.geometry!} />}

      {/* Elevation Profile — only if geometry has elevation data */}
      {hasGeometry && data.geometry!.some((p) => p.ele != null) && (
        <Card>
          <CardHeader title="Hoehenprofil" />
          <ElevationProfile geometry={data.geometry!} />
        </Card>
      )}

      {/* Weather at trail location */}
      {weatherHours.length > 0 && (
        <Card>
          <CardHeader title="Wetter vor Ort" />
          <div className="flex gap-3 overflow-x-auto pb-1">
            {weatherHours.map((h, i) => {
              const time = new Date(h.time);
              const hour = time.getHours().toString().padStart(2, "0");
              return (
                <div
                  key={i}
                  className="flex flex-col items-center gap-1 min-w-[48px] text-center"
                >
                  <span className="text-[10px] text-text-muted">{hour}:00</span>
                  <span className="text-lg">{weatherIcon(h.condition)}</span>
                  <span className="text-xs font-semibold">{Math.round(h.temp_c)}&deg;</span>
                  {h.precipitation_mm > 0 && (
                    <span className="text-[10px] text-accent-blue">
                      {h.precipitation_mm.toFixed(1)}mm
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Trail condition */}
      {data.condition && (
        <Card>
          <CardHeader title="Trail Zustand" />
          <div className="flex items-center justify-between">
            <div>
              <Badge variant={conditionVariant(data.condition.condition)}>
                {data.condition.condition}
              </Badge>
              <p className="mt-2 text-xs text-text-secondary">
                Oberflaeche: {data.condition.surface}
              </p>
              <p className="mt-1 text-[11px] text-text-muted">
                Konfidenz: {data.condition.confidence}
              </p>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold text-accent-blue">
                {data.condition.rain_48h_mm}{" "}
                <span className="text-xs font-normal">mm</span>
              </p>
              <p className="text-[11px] text-text-muted">Regen 48h</p>
            </div>
          </div>
        </Card>
      )}

      {/* Description */}
      {data.description && (
        <Card>
          <CardHeader title="Beschreibung" />
          <p className="text-sm text-text-secondary leading-relaxed">
            {data.description}
          </p>
        </Card>
      )}

      {/* GPX Download */}
      {user && hasGeometry && (
        <button
          onClick={() => downloadGpx(data.name || `Trail_${data.osm_id}`, data.geometry!)}
          className="w-full flex items-center justify-center gap-2 bg-accent-green/15 text-accent-green font-semibold text-sm py-3 rounded-xl border border-accent-green/20 hover:bg-accent-green/25 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          GPX herunterladen
        </button>
      )}

      {/* Similar trails */}
      {similarTrails.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold uppercase tracking-wider text-text-secondary mb-3">
            In der Naehe
          </h3>
          <div className="space-y-2">
            {similarTrails.map((trail) => (
              <TrailCard key={trail.osm_id} trail={trail} />
            ))}
          </div>
        </div>
      )}

      {/* Tags */}
      {data.tags && Object.keys(data.tags).length > 0 && (
        <Card>
          <CardHeader title="Tags" />
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.tags).map(([key, value]) => (
              <Badge key={key} variant="gray">
                {key}: {value}
              </Badge>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
