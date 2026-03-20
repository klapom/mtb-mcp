import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import type { Trail } from "@/lib/types";

const conditionDots: Record<string, string> = {
  dry: "bg-s0",
  damp: "bg-s1",
  wet: "bg-s2",
  muddy: "bg-s3",
};

export function TrailCard({ trail }: { trail: Trail }) {
  const dot = trail.condition
    ? conditionDots[trail.condition.condition] ?? "bg-text-muted"
    : "bg-text-muted";

  return (
    <Link
      href={`/trails/${trail.osm_id}`}
      className="block bg-bg-card border border-border-card rounded-xl p-4 shadow-[0_2px_12px_rgba(0,0,0,0.3)] hover:shadow-[0_4px_16px_rgba(0,0,0,0.35)] transition-shadow"
      data-testid="trail-card"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm truncate flex-1">
          {trail.name || `Trail ${trail.osm_id}`}
        </h3>
        <div className="flex items-center gap-2">
          <Badge variant={trail.difficulty?.toLowerCase()}>
            {trail.difficulty}
          </Badge>
          <span className={`w-2.5 h-2.5 rounded-full ${dot}`} data-testid="condition-dot" />
        </div>
      </div>
      <div className="flex gap-4 text-xs text-text-secondary">
        <span>{(trail.length_m / 1000).toFixed(1)} km</span>
        <span>{trail.surface}</span>
      </div>
    </Link>
  );
}
