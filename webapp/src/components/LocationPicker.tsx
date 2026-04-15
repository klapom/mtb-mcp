'use client';

import { useState, useEffect, useCallback } from 'react';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org';
const STORAGE_KEY = 'trailpilot_search_location';

export interface SearchLocation {
  lat: number;
  lon: number;
  label: string;
}

function loadLocation(): SearchLocation | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as SearchLocation;
  } catch { /* ignore */ }
  return null;
}

function saveLocation(loc: SearchLocation) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(loc));
  }
}

export function useSearchLocation(userHome?: { lat: number; lon: number } | null) {
  const [location, setLocation] = useState<SearchLocation | null>(null);

  useEffect(() => {
    const saved = loadLocation();
    if (saved) {
      setLocation(saved);
    } else if (userHome?.lat && userHome?.lon) {
      // Use user's home location as default
      const homeLoc: SearchLocation = {
        lat: userHome.lat,
        lon: userHome.lon,
        label: `Heimat (${userHome.lat.toFixed(2)}, ${userHome.lon.toFixed(2)})`,
      };
      setLocation(homeLoc);
      saveLocation(homeLoc);
    }
  }, [userHome?.lat, userHome?.lon]);

  const updateLocation = useCallback((loc: SearchLocation) => {
    setLocation(loc);
    saveLocation(loc);
  }, []);

  const clearLocation = useCallback(() => {
    setLocation(null);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  return { location, updateLocation, clearLocation };
}

export function LocationPicker({
  location,
  onLocationChange,
}: {
  location: SearchLocation | null;
  onLocationChange: (loc: SearchLocation) => void;
}) {
  const [address, setAddress] = useState('');
  const [searching, setSearching] = useState(false);
  const [geolocating, setGeolocating] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);

  async function handleSearch() {
    if (!address.trim()) return;
    setSearching(true);
    setError('');
    try {
      const resp = await fetch(
        `${NOMINATIM_URL}/search?q=${encodeURIComponent(address)}&format=json&limit=1&accept-language=de`,
      );
      const results = await resp.json();
      if (results.length === 0) {
        setError('Nicht gefunden');
        return;
      }
      const r = results[0];
      const label = r.display_name.split(', ').slice(0, 2).join(', ');
      onLocationChange({ lat: parseFloat(r.lat), lon: parseFloat(r.lon), label });
      setExpanded(false);
      setAddress('');
    } catch {
      setError('Suche fehlgeschlagen');
    } finally {
      setSearching(false);
    }
  }

  function handleGPS() {
    if (!('geolocation' in navigator)) {
      setError('GPS nicht verfuegbar');
      return;
    }
    setGeolocating(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        let label = `${latitude.toFixed(2)}, ${longitude.toFixed(2)}`;
        try {
          const resp = await fetch(
            `${NOMINATIM_URL}/reverse?lat=${latitude}&lon=${longitude}&format=json&accept-language=de`,
          );
          const data = await resp.json();
          if (data.display_name) {
            label = data.display_name.split(', ').slice(0, 2).join(', ');
          }
        } catch { /* keep coordinate label */ }
        onLocationChange({ lat: latitude, lon: longitude, label });
        setExpanded(false);
        setGeolocating(false);
      },
      () => {
        setError('Standort nicht ermittelbar');
        setGeolocating(false);
      },
    );
  }

  return (
    <div className="bg-bg-card rounded-xl border border-border-card overflow-hidden">
      {/* Collapsed: show current location */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left"
      >
        <span className="text-base">📍</span>
        <span className="flex-1 text-sm truncate">
          {location ? (
            <span className="text-white">{location.label}</span>
          ) : (
            <span className="text-text-muted">Standort waehlen...</span>
          )}
        </span>
        <span className={`text-text-muted text-xs transition-transform ${expanded ? 'rotate-180' : ''}`}>
          ▾
        </span>
      </button>

      {/* Expanded: search + GPS */}
      {expanded && (
        <div className="px-3 pb-3 flex flex-col gap-2 border-t border-border-subtle pt-2">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Adresse, Ort oder PLZ"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSearch(); } }}
              className="flex-1 px-2.5 py-2 rounded-lg bg-bg-primary border border-border-subtle text-white text-xs placeholder:text-text-muted focus:outline-none focus:border-accent-green"
            />
            <button
              type="button"
              onClick={handleSearch}
              disabled={searching || !address.trim()}
              className="px-3 py-2 rounded-lg bg-accent-green/20 text-accent-green text-xs font-medium disabled:opacity-40"
            >
              {searching ? '...' : 'OK'}
            </button>
          </div>
          <button
            type="button"
            onClick={handleGPS}
            disabled={geolocating}
            className="flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-lg bg-white/6 text-text-muted text-xs hover:bg-white/10 disabled:opacity-40"
          >
            <span>📡</span>
            {geolocating ? 'Ermittle...' : 'GPS verwenden'}
          </button>
          {error && <p className="text-red-400 text-xs text-center">{error}</p>}
        </div>
      )}
    </div>
  );
}
