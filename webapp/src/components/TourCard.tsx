import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import type { TourSummary } from "@/lib/types";

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function TourCard({ tour }: { tour: TourSummary }) {
  return (
    <Link
      href={`/tours/${tour.source}/${tour.id}`}
      className="block bg-bg-card border border-border-card rounded-xl p-4 shadow-[0_2px_12px_rgba(0,0,0,0.3)] hover:shadow-[0_4px_16px_rgba(0,0,0,0.35)] transition-shadow"
      data-testid="tour-card"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm truncate flex-1">{tour.name}</h3>
        <Badge variant={tour.source === "komoot" ? "blue" : "orange"}>
          {tour.source === "komoot" ? "Komoot" : "GPS-Tour"}
        </Badge>
      </div>
      <div className="flex gap-4 text-xs text-text-secondary">
        {tour.distance_km != null && (
          <span data-testid="tour-distance">{tour.distance_km.toFixed(1)} km</span>
        )}
        {(tour.elevation_up_m ?? tour.elevation_m) != null && (
          <span data-testid="tour-elevation">↑ {tour.elevation_up_m ?? tour.elevation_m} m</span>
        )}
        {tour.duration_minutes != null && (
          <span data-testid="tour-duration">{formatDuration(tour.duration_minutes)}</span>
        )}
      </div>
    </Link>
  );
}
