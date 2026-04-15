"use client";

import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useCachedApi } from "@/hooks/useCachedApi";
import { useAuth } from "@/contexts/AuthContext";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { TrailCard } from "@/components/TrailCard";
import { TourCard } from "@/components/TourCard";
import { LocationPicker, useSearchLocation } from "@/components/LocationPicker";
import type { Trail, TourSummary } from "@/lib/types";

// --- Constants ---

const ALL_DIFFICULTIES = ["S0", "S1", "S2", "S3", "S4", "S5"] as const;

const SURFACE_OPTIONS: { value: string; label: string }[] = [
  { value: "dirt", label: "Erde" },
  { value: "gravel", label: "Schotter" },
  { value: "rock", label: "Fels" },
  { value: "roots", label: "Wurzeln" },
];

const DIFFICULTY_ORDER: Record<string, number> = {
  S0: 0, S1: 1, S2: 2, S3: 3, S4: 4, S5: 5, S6: 6,
};

type SortKey = "length_asc" | "length_desc" | "difficulty_asc" | "difficulty_desc" | "name";
type ViewTab = "all" | "trails" | "tours";

const sortOptions: { value: SortKey; label: string }[] = [
  { value: "length_asc", label: "Kurz → lang" },
  { value: "length_desc", label: "Lang → kurz" },
  { value: "difficulty_asc", label: "Leicht → schwer" },
  { value: "difficulty_desc", label: "Schwer → leicht" },
  { value: "name", label: "Name A-Z" },
];

const MAX_LENGTH_KM = 50;

// --- Persistence ---

const STORAGE_KEY = "trailpilot_explore_filters";

interface SavedFilters {
  tab: ViewTab;
  minDifficulty: number;
  maxDifficulty: number;
  minLengthKm: number;
  maxLengthKm: number;
  surfaces: string[];
  sortBy: SortKey;
  radius: number;
  query: string;
}

const DEFAULTS: SavedFilters = {
  tab: "all",
  minDifficulty: 0,
  maxDifficulty: 5,
  minLengthKm: 0,
  maxLengthKm: MAX_LENGTH_KM,
  surfaces: [],
  sortBy: "length_asc",
  radius: 30,
  query: "",
};

function loadFilters(): SavedFilters {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULTS;
}

function saveFilters(f: SavedFilters) {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(f));
  }
}

// --- Geo helper ---

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function trailLat(t: Trail): number | null {
  if (t.lat) return t.lat;
  if (t.geometry?.length) return t.geometry[0].lat;
  return null;
}

function trailLon(t: Trail): number | null {
  if (t.lon) return t.lon;
  if (t.geometry?.length) return t.geometry[0].lon;
  return null;
}

// --- Unified item type ---

interface ExploreItem {
  type: "trail" | "tour";
  id: string;
  name: string;
  lengthKm: number;
  difficulty: string;
  surface?: string;
  distanceKm?: number;
  trail?: Trail;
  tour?: TourSummary;
}

function trailToItem(t: Trail): ExploreItem {
  return {
    type: "trail",
    id: `trail-${t.osm_id}`,
    name: t.name || `Trail ${t.osm_id}`,
    lengthKm: t.length_m / 1000,
    difficulty: t.mtb_scale || "?",
    surface: t.surface,
    trail: t,
  };
}

function tourToItem(t: TourSummary): ExploreItem {
  return {
    type: "tour",
    id: `tour-${t.source}-${t.id}`,
    name: t.name,
    lengthKm: t.distance_km ?? 0,
    difficulty: t.difficulty ?? "?",
    tour: t,
  };
}

// --- Components ---

function ToggleChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
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

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-colors ${
        active ? "bg-accent-green/20 text-accent-green" : "text-text-muted hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}

function DualRange({
  label,
  minVal,
  maxVal,
  absMin,
  absMax,
  step,
  unit,
  onMinChange,
  onMaxChange,
}: {
  label: string;
  minVal: number;
  maxVal: number;
  absMin: number;
  absMax: number;
  step: number;
  unit: string;
  onMinChange: (v: number) => void;
  onMaxChange: (v: number) => void;
}) {
  const minLabel = minVal <= absMin ? `${absMin}` : `${minVal}`;
  const maxLabel = maxVal >= absMax ? `${absMax}+` : `${maxVal}`;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between text-xs">
        <span className="text-text-muted">{label}</span>
        <span className="text-white font-medium">{minLabel} – {maxLabel} {unit}</span>
      </div>
      <div className="flex gap-3 items-center">
        <span className="text-[10px] text-text-muted w-8 text-right">Min</span>
        <input
          type="range" min={absMin} max={absMax} step={step} value={minVal}
          onChange={(e) => onMinChange(Math.min(Number(e.target.value), maxVal))}
          className="flex-1 h-1.5 rounded-full appearance-none bg-white/10 accent-accent-green cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent-green"
        />
      </div>
      <div className="flex gap-3 items-center">
        <span className="text-[10px] text-text-muted w-8 text-right">Max</span>
        <input
          type="range" min={absMin} max={absMax} step={step} value={maxVal}
          onChange={(e) => onMaxChange(Math.max(Number(e.target.value), minVal))}
          className="flex-1 h-1.5 rounded-full appearance-none bg-white/10 accent-accent-green cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent-green"
        />
      </div>
    </div>
  );
}

// --- Page ---

export default function ExplorePage() {
  const [tab, setTab] = useState<ViewTab>(DEFAULTS.tab);
  const [minDifficulty, setMinDifficulty] = useState(DEFAULTS.minDifficulty);
  const [maxDifficulty, setMaxDifficulty] = useState(DEFAULTS.maxDifficulty);
  const [minLengthKm, setMinLengthKm] = useState(DEFAULTS.minLengthKm);
  const [maxLengthKm, setMaxLengthKm] = useState(DEFAULTS.maxLengthKm);
  const [surfaces, setSurfaces] = useState<string[]>(DEFAULTS.surfaces);
  const [sortBy, setSortBy] = useState<SortKey>(DEFAULTS.sortBy);
  const [radius, setRadius] = useState(DEFAULTS.radius);
  const [query, setQuery] = useState(DEFAULTS.query);
  const [debouncedQuery, setDebouncedQuery] = useState(DEFAULTS.query);
  const [filtersLoaded, setFiltersLoaded] = useState(false);

  // Restore saved filters after mount (avoids hydration mismatch)
  useEffect(() => {
    const saved = loadFilters();
    setTab(saved.tab); setMinDifficulty(saved.minDifficulty); setMaxDifficulty(saved.maxDifficulty);
    setMinLengthKm(saved.minLengthKm); setMaxLengthKm(saved.maxLengthKm);
    setSurfaces(saved.surfaces); setSortBy(saved.sortBy); setRadius(saved.radius);
    setQuery(saved.query); setDebouncedQuery(saved.query);
    setFiltersLoaded(true);
  }, []);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { user } = useAuth();
  const { location, updateLocation } = useSearchLocation(
    user ? { lat: user.home_lat ?? 0, lon: user.home_lon ?? 0 } : null,
  );

  // Debounce search
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(query), 500);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [query]);

  // Persist (only after initial load to avoid overwriting with defaults)
  useEffect(() => {
    if (!filtersLoaded) return;
    saveFilters({ tab, minDifficulty, maxDifficulty, minLengthKm, maxLengthKm, surfaces, sortBy, radius, query: debouncedQuery });
  }, [filtersLoaded, tab, minDifficulty, maxDifficulty, minLengthKm, maxLengthKm, surfaces, sortBy, radius, debouncedQuery]);

  function toggleSurface(s: string) {
    setSurfaces((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  // --- API queries (one call per source with max radius, rest is client-side) ---
  const FETCH_RADIUS = 50; // always fetch 50km, filter by user radius client-side
  const locParams = location ? `&lat=${location.lat}&lon=${location.lon}` : "";

  // Trails: one cached call per location (1h TTL)
  const trailPath = (tab === "tours") ? null : `/trails?radius_km=${FETCH_RADIUS}${locParams}`;
  // Tours: cached + query param (30min TTL)
  const tourParams = new URLSearchParams({ radius_km: String(FETCH_RADIUS) });
  if (location) { tourParams.set("lat", String(location.lat)); tourParams.set("lon", String(location.lon)); }
  if (debouncedQuery.trim()) tourParams.set("query", debouncedQuery.trim());
  const tourPath = (tab === "trails") ? null : `/tours/search?${tourParams.toString()}`;

  const { data: trails, error: trailError, isLoading: trailLoading } = useCachedApi<Trail[]>(trailPath, 60 * 60 * 1000);
  const { data: tours, error: tourError, isLoading: tourLoading } = useCachedApi<TourSummary[]>(tourPath, 30 * 60 * 1000);

  const isLoading = trailLoading || tourLoading;
  const error = trailError || tourError;

  // --- Merge + filter + sort ---
  const items = useMemo(() => {
    const all: ExploreItem[] = [];

    // Add trails with distance calculation
    if (tab !== "tours" && trails) {
      for (const t of trails) {
        const item = trailToItem(t);
        if (location) {
          const tLat = trailLat(t);
          const tLon = trailLon(t);
          if (tLat !== null && tLon !== null) {
            item.distanceKm = haversineKm(location.lat, location.lon, tLat, tLon);
          }
        }
        all.push(item);
      }
    }
    if (tab !== "trails" && tours) {
      all.push(...tours.map(tourToItem));
    }

    // Filter
    const filtered = all.filter((item) => {
      // Radius filter (client-side, trails only — tours are already filtered by API)
      if (item.distanceKm !== undefined && item.distanceKm > radius) return false;
      // Difficulty range (trails)
      if (item.type === "trail") {
        const diff = DIFFICULTY_ORDER[item.difficulty] ?? -1;
        if (diff >= 0 && (diff < minDifficulty || diff > maxDifficulty)) return false;
      }
      // Length range
      if (item.lengthKm < minLengthKm) return false;
      if (maxLengthKm < MAX_LENGTH_KM && item.lengthKm > maxLengthKm) return false;
      // Surface (trails only)
      if (surfaces.length > 0 && item.surface && !surfaces.includes(item.surface)) return false;
      // Text search
      if (debouncedQuery.trim() && item.type === "trail") {
        if (!item.name.toLowerCase().includes(debouncedQuery.toLowerCase())) return false;
      }
      return true;
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "length_asc": return a.lengthKm - b.lengthKm;
        case "length_desc": return b.lengthKm - a.lengthKm;
        case "difficulty_asc": return (DIFFICULTY_ORDER[a.difficulty] ?? 99) - (DIFFICULTY_ORDER[b.difficulty] ?? 99);
        case "difficulty_desc": return (DIFFICULTY_ORDER[b.difficulty] ?? 99) - (DIFFICULTY_ORDER[a.difficulty] ?? 99);
        case "name": return a.name.localeCompare(b.name);
        default: return 0;
      }
    });

    return filtered;
  }, [trails, tours, tab, minDifficulty, maxDifficulty, minLengthKm, maxLengthKm, surfaces, sortBy, debouncedQuery, radius, location]);

  const totalRaw = (tab !== "tours" ? (trails?.length ?? 0) : 0) + (tab !== "trails" ? (tours?.length ?? 0) : 0);
  const hasActiveFilters = minDifficulty > 0 || maxDifficulty < 5 || minLengthKm > 0 || maxLengthKm < MAX_LENGTH_KM || surfaces.length > 0 || debouncedQuery.trim() !== "";

  const resetFilters = useCallback(() => {
    setMinDifficulty(0); setMaxDifficulty(5);
    setMinLengthKm(0); setMaxLengthKm(MAX_LENGTH_KM);
    setSurfaces([]); setSortBy("length_asc");
    setQuery(""); setDebouncedQuery("");
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold">Entdecken</h1>
        {hasActiveFilters && (
          <button onClick={resetFilters} className="text-xs text-accent-green hover:underline">
            Filter zuruecksetzen
          </button>
        )}
      </div>

      {/* Location */}
      <LocationPicker location={location} onLocationChange={updateLocation} />

      {/* Tab: Alle / Trails / Touren */}
      <div className="flex gap-1 bg-bg-card rounded-lg border border-border-card p-1">
        <TabButton label="Alle" active={tab === "all"} onClick={() => setTab("all")} />
        <TabButton label="Trails" active={tab === "trails"} onClick={() => setTab("trails")} />
        <TabButton label="Touren" active={tab === "tours"} onClick={() => setTab("tours")} />
      </div>

      {/* Search */}
      <input
        type="text"
        placeholder="Suchen..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full bg-bg-card border border-border-card rounded-lg p-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent-green/40 transition-colors"
      />

      {/* Surface chips (visible for trails) */}
      {tab !== "tours" && (
        <div>
          <p className="text-xs text-text-muted mb-1.5">Untergrund</p>
          <div className="flex flex-wrap gap-2">
            {SURFACE_OPTIONS.map((s) => (
              <ToggleChip key={s.value} label={s.label} active={surfaces.includes(s.value)} onClick={() => toggleSurface(s.value)} />
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-4">
        {/* Radius */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-text-muted">Radius</span>
            <span className="text-white font-medium">{radius} km</span>
          </div>
          <input type="range" min={5} max={100} step={5} value={radius}
            onChange={(e) => setRadius(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none bg-white/10 accent-accent-green cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent-green"
          />
        </div>

        {/* Difficulty (trails) */}
        {tab !== "tours" && (
          <>
            <DualRange label="Schwierigkeit" minVal={minDifficulty} maxVal={maxDifficulty}
              absMin={0} absMax={5} step={1} unit=""
              onMinChange={setMinDifficulty} onMaxChange={setMaxDifficulty} />
            <div className="flex justify-between text-[10px] text-text-muted -mt-2 px-9">
              {ALL_DIFFICULTIES.map((d) => <span key={d}>{d}</span>)}
            </div>
          </>
        )}

        {/* Length */}
        <DualRange label="Laenge" minVal={minLengthKm} maxVal={maxLengthKm}
          absMin={0} absMax={MAX_LENGTH_KM} step={1} unit="km"
          onMinChange={setMinLengthKm} onMaxChange={setMaxLengthKm} />

        {/* Sort */}
        <div className="flex items-center justify-between pt-1 border-t border-border-subtle">
          <span className="text-xs text-text-muted">Sortierung</span>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortKey)}
            className="bg-bg-primary border border-border-subtle text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-accent-green">
            {sortOptions.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </div>
      </div>

      {/* Results */}
      {isLoading && <LoadingState text="Suche..." />}
      {error && <ErrorState message={error.message} onRetry={() => {}} />}
      {!isLoading && !error && items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
          <span className="text-3xl">&#x1F6B5;</span>
          <p className="text-sm text-text-secondary">
            {hasActiveFilters ? "Nichts mit diesen Filtern gefunden" : "Nichts in der Naehe gefunden"}
          </p>
          {hasActiveFilters && (
            <button onClick={resetFilters} className="text-xs text-accent-green hover:underline">Filter zuruecksetzen</button>
          )}
        </div>
      )}
      {items.length > 0 && (
        <>
          <p className="text-xs text-text-muted">
            {items.length} Ergebnis{items.length !== 1 ? "se" : ""}
            {items.length < totalRaw && ` (${totalRaw - items.length} gefiltert)`}
          </p>
          <div className="space-y-2">
            {items.map((item) =>
              item.trail ? (
                <TrailCard key={item.id} trail={item.trail} />
              ) : item.tour ? (
                <TourCard key={item.id} tour={item.tour} />
              ) : null,
            )}
          </div>
        </>
      )}
    </div>
  );
}
