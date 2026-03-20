"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Tours } from "@/lib/api";
import type { TourDetail } from "@/lib/types";

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function TourDetailPage() {
  const { source, id } = useParams<{ source: string; id: string }>();
  const { data, error, isLoading, mutate } = useApi<TourDetail>(
    source && id ? `/tours/${source}/${id}` : null
  );

  if (isLoading) return <LoadingState text="Tour laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  const sourceVariant = data.source === "komoot" ? "blue" : "orange";
  const sourceLabel = data.source === "komoot" ? "Komoot" : "GPS-Tour";

  return (
    <div className="space-y-4">
      {/* Back link */}
      <Link
        href="/tours"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary transition-colors"
      >
        &larr; Touren
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold flex-1">{data.name}</h1>
        <Badge variant={sourceVariant}>{sourceLabel}</Badge>
      </div>

      {/* Stats row */}
      <div className="flex gap-4 text-sm text-text-secondary">
        <span>{data.distance_km.toFixed(1)} km</span>
        <span>&uarr; {data.elevation_up_m} m</span>
        <span>&darr; {data.elevation_down_m} m</span>
        <span>{formatDuration(data.duration_minutes)}</span>
      </div>

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
      {data.segments.length > 0 && (
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
      {data.gpx_available && source && id && (
        <a
          href={Tours.gpxUrl(source, id)}
          download
          className="block w-full text-center px-4 py-3 bg-accent-green text-white text-sm font-semibold rounded-lg hover:bg-[#0db365] transition-colors"
        >
          GPX Herunterladen
        </a>
      )}
    </div>
  );
}
