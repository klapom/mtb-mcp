"use client";

import { useState, useEffect, useRef } from "react";
import { useApi } from "@/hooks/useApi";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { TourCard } from "@/components/TourCard";
import type { TourSummary } from "@/lib/types";

export default function ToursPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [radius, setRadius] = useState(30);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search input by 500ms
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedQuery(query);
    }, 500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  const params = new URLSearchParams({ radius_km: String(radius) });
  if (debouncedQuery.trim()) params.set("query", debouncedQuery.trim());
  const path = `/tours/search?${params.toString()}`;

  const { data, error, isLoading, mutate } = useApi<TourSummary[]>(path);

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Touren</h1>

      {/* Search input */}
      <input
        type="text"
        placeholder="Tour suchen..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full bg-bg-input border border-border-card rounded-lg p-2.5 text-text-primary placeholder:text-text-muted outline-none focus:border-accent-green/40 transition-colors"
      />

      {/* Radius slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <label className="text-xs text-text-secondary">Radius</label>
          <span className="text-xs text-text-secondary font-semibold">
            {radius} km
          </span>
        </div>
        <input
          type="range"
          min={10}
          max={100}
          step={5}
          value={radius}
          onChange={(e) => setRadius(Number(e.target.value))}
          className="w-full accent-accent-green"
        />
      </div>

      {/* Content */}
      {isLoading && <LoadingState text="Touren suchen..." />}
      {error && <ErrorState message={error.message} onRetry={() => mutate()} />}
      {data && data.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
          <span className="text-3xl">&#x1F5FA;</span>
          <p className="text-sm text-text-secondary">
            Keine Touren gefunden
          </p>
        </div>
      )}
      {data && data.length > 0 && (
        <div className="space-y-2">
          {data.map((tour) => (
            <TourCard key={`${tour.source}-${tour.id}`} tour={tour} />
          ))}
        </div>
      )}
    </div>
  );
}
