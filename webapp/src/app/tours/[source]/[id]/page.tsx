"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useState, useMemo, useCallback } from "react";
import { useParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { TrailCard } from "@/components/TrailCard";
import { Tours } from "@/lib/api";
import type { TourDetail, Trail } from "@/lib/types";

const TourRouteMap = dynamic(
  () => import("@/components/TourRouteMap").then((m) => ({ default: m.TourRouteMap })),
  { ssr: false },
);

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function TourDetailPage() {
  const { source, id } = useParams<{ source: string; id: string }>();
  const { user } = useAuth();
  const [corridorKm, setCorridorKm] = useState(1.0);
  const { data, error, isLoading, mutate } = useApi<TourDetail>(
    source && id ? `/tours/${source}/${id}` : null,
  );

  // Fetch trail fragments along route
  const tourLat = data?.start_lat;
  const tourLon = data?.start_lon;
  const hasWaypoints = tourLat != null && tourLon != null;

  // Build waypoints from tour data (start point + segments if available)
  const waypoints = useMemo(() => {
    if (!data) return null;
    const pts: number[][] = [];
    if (data.start_lat != null && data.start_lon != null) {
      pts.push([data.start_lat, data.start_lon]);
    }
    // If we have segment waypoints they'd be here, but for now just use start
    return pts.length >= 1 ? pts : null;
  }, [data]);

  // Nearby trails (use start point as center, wider radius to cover the route)
  const searchRadius = Math.max(5, Math.ceil((data?.distance_km ?? 10) / 2 + corridorKm));
  const { data: nearbyTrails, isLoading: trailsLoading } = useApi<Trail[]>(
    hasWaypoints ? `/trails?radius_km=${searchRadius}&lat=${tourLat}&lon=${tourLon}` : null,
  );

  // Filter fragments by corridor distance (all lengths, not just >200m)
  const trailFragments = useMemo(() => {
    if (!nearbyTrails || !hasWaypoints) return [];
    return nearbyTrails;
  }, [nearbyTrails, hasWaypoints]);

  if (isLoading) return <LoadingState text="Tour laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  const sourceVariant = data.source === "komoot" ? "blue" : "orange";
  const sourceLabel = data.source === "komoot" ? "Komoot" : "GPS-Tour";

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
        <h1 className="text-xl font-bold flex-1">{data.name}</h1>
        <Badge variant={sourceVariant}>{sourceLabel}</Badge>
      </div>

      {/* Stats row */}
      <div className="flex gap-4 text-sm text-text-secondary">
        {data.distance_km != null && <span>{data.distance_km.toFixed(1)} km</span>}
        {(data.elevation_up_m ?? data.elevation_m) != null && (
          <span>&uarr; {data.elevation_up_m ?? data.elevation_m} m</span>
        )}
        {data.duration_minutes != null && data.duration_minutes > 0 && (
          <span>{formatDuration(data.duration_minutes)}</span>
        )}
      </div>

      {/* Map with tour start + nearby trail fragments */}
      {hasWaypoints && (
        <TourRouteMap
          tourStart={[tourLat!, tourLon!]}
          tourName={data.name}
          trailFragments={trailFragments}
          corridorKm={corridorKm}
        />
      )}

      {/* Trail Fragments along route */}
      {hasWaypoints && (
        <Card>
          <CardHeader title="Trail-Fragmente entlang der Route" />
          <p className="text-xs text-text-muted mb-3">
            Entdecke Singletrails in der Naehe deiner Tour, die du als Abstecher mitnehmen kannst.
          </p>

          {/* Corridor slider */}
          <div className="flex flex-col gap-1.5 mb-4">
            <div className="flex justify-between text-xs">
              <span className="text-text-muted">Korridor</span>
              <span className="text-white font-medium">{corridorKm.toFixed(1)} km</span>
            </div>
            <input
              type="range"
              min={0.1}
              max={5}
              step={0.1}
              value={corridorKm}
              onChange={(e) => setCorridorKm(Number(e.target.value))}
              className="w-full h-1.5 rounded-full appearance-none bg-white/10 accent-accent-green cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent-green"
            />
          </div>

          {trailsLoading && <LoadingState text="Suche Trails..." />}
          {trailFragments.length === 0 && !trailsLoading && (
            <p className="text-xs text-text-muted text-center py-4">
              Keine Trail-Fragmente im Korridor gefunden
            </p>
          )}
          {trailFragments.length > 0 && (
            <>
              <p className="text-xs text-text-muted mb-2">
                {trailFragments.length} Trail{trailFragments.length !== 1 ? "s" : ""} gefunden
              </p>
              <div className="space-y-2">
                {trailFragments.map((trail) => (
                  <TrailCard key={trail.osm_id} trail={trail} />
                ))}
              </div>
            </>
          )}
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

      {/* Segments */}
      {data.segments && data.segments.length > 0 && (
        <Card>
          <CardHeader title="Segmente" />
          <div className="space-y-2">
            {data.segments.map((seg, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between bg-white/4 rounded-lg px-3 py-2"
              >
                <span className="text-sm">{seg.name}</span>
                <div className="flex items-center gap-3 text-xs text-text-secondary">
                  <span>{seg.distance_km.toFixed(1)} km</span>
                  <Badge variant={seg.difficulty?.toLowerCase() ?? "gray"}>
                    {seg.difficulty}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* GPX Download button */}
      {data.gpx_available && source && id && user && (
        <a
          href={Tours.gpxUrl(source, id)}
          download
          className="block w-full text-center px-4 py-3 bg-accent-green text-white text-sm font-semibold rounded-lg hover:bg-[#0db365] transition-colors"
        >
          GPX Herunterladen
        </a>
      )}

      {/* Komoot link */}
      {data.url && (
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full text-center px-4 py-2.5 bg-white/6 text-text-muted text-sm rounded-lg hover:bg-white/10 transition-colors"
        >
          Auf {sourceLabel} ansehen &rarr;
        </a>
      )}
    </div>
  );
}
