"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useApi } from "@/hooks/useApi";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import type { TrailDetail } from "@/lib/types";

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

export default function TrailDetailPage() {
  const { osmId } = useParams<{ osmId: string }>();
  const { data, error, isLoading, mutate } = useApi<TrailDetail>(
    osmId ? `/trails/${osmId}` : null
  );

  if (isLoading) return <LoadingState text="Trail laden..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;
  if (!data) return null;

  const tags = Object.entries(data.tags);

  return (
    <div className="space-y-4">
      {/* Back link */}
      <Link
        href="/trails"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary transition-colors"
      >
        &larr; Trails
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold flex-1">
          {data.name || `Trail ${data.osm_id}`}
        </h1>
        <Badge variant={data.difficulty?.toLowerCase()}>{data.difficulty}</Badge>
      </div>

      {/* Basic info */}
      <div className="flex gap-4 text-sm text-text-secondary">
        <span>{(data.length_m / 1000).toFixed(1)} km</span>
        <span>{data.surface}</span>
        <span>&uarr; {data.elevation_gain_m} m</span>
      </div>

      {/* Trail condition */}
      <Card>
        <CardHeader title="Trail Zustand" />
        <div className="flex items-center justify-between">
          <div>
            <Badge variant={conditionVariant(data.condition.condition)}>
              {data.condition.condition}
            </Badge>
            <p className="mt-2 text-xs text-text-secondary">
              Oberfl&auml;che: {data.condition.surface}
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

      {/* Description */}
      {data.description && (
        <Card>
          <CardHeader title="Beschreibung" />
          <p className="text-sm text-text-secondary leading-relaxed">
            {data.description}
          </p>
        </Card>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <Card>
          <CardHeader title="Tags" />
          <div className="flex flex-wrap gap-2">
            {tags.map(([key, value]) => (
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
