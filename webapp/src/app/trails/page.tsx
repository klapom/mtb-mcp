"use client";

import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { TrailCard } from "@/components/TrailCard";
import type { Trail } from "@/lib/types";

const difficulties = ["All", "S0", "S1", "S2", "S3"] as const;
const surfaces = ["All", "dirt", "gravel", "rock", "roots"] as const;

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
        active
          ? "bg-accent-green/20 text-accent-green border-accent-green/30"
          : "bg-white/6 text-text-secondary border-transparent"
      }`}
    >
      {label}
    </button>
  );
}

export default function TrailsPage() {
  const [difficulty, setDifficulty] = useState<string>("All");
  const [surface, setSurface] = useState<string>("All");

  const params = new URLSearchParams({ radius_km: "30" });
  if (difficulty !== "All") params.set("min_difficulty", difficulty);
  if (surface !== "All") params.set("surface", surface);
  const path = `/trails?${params.toString()}`;

  const { data, error, isLoading, mutate } = useApi<Trail[]>(path);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Trails</h1>

      {/* Difficulty filter chips */}
      <div className="flex flex-wrap gap-2">
        {difficulties.map((d) => (
          <Chip
            key={d}
            label={d}
            active={difficulty === d}
            onClick={() => setDifficulty(d)}
          />
        ))}
      </div>

      {/* Surface filter chips */}
      <div className="flex flex-wrap gap-2">
        {surfaces.map((s) => (
          <Chip
            key={s}
            label={s}
            active={surface === s}
            onClick={() => setSurface(s)}
          />
        ))}
      </div>

      {/* Content */}
      {isLoading && <LoadingState text="Trails laden..." />}
      {error && <ErrorState message={error.message} onRetry={() => mutate()} />}
      {data && data.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
          <span className="text-3xl">&#x1F6B5;</span>
          <p className="text-sm text-text-secondary">
            Keine Trails in der N&auml;he gefunden
          </p>
        </div>
      )}
      {data && data.length > 0 && (
        <div className="space-y-2">
          {data.map((trail) => (
            <TrailCard key={trail.osm_id} trail={trail} />
          ))}
        </div>
      )}
    </div>
  );
}
