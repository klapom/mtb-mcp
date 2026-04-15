'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org';

export default function SetupPage() {
  const { user, completeOnboarding } = useAuth();
  const router = useRouter();
  const [address, setAddress] = useState('');
  const [resolvedAddress, setResolvedAddress] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [bikeName, setBikeName] = useState('');
  const [bikeType, setBikeType] = useState('mtb');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [geolocating, setGeolocating] = useState(false);

  useEffect(() => {
    if (user?.onboarding_done) {
      router.replace('/');
    }
  }, [user, router]);

  useEffect(() => {
    if (!user) {
      router.replace('/login');
    }
  }, [user, router]);

  const reverseGeocode = useCallback(async (latitude: number, longitude: number) => {
    try {
      const resp = await fetch(
        `${NOMINATIM_URL}/reverse?lat=${latitude}&lon=${longitude}&format=json&accept-language=de`,
      );
      const data = await resp.json();
      if (data.display_name) {
        // Shorten: take city/town + state, skip full address
        const parts = data.display_name.split(', ');
        const short = parts.length > 3
          ? `${parts[0]}, ${parts[1]}, ${parts[parts.length - 3]}`
          : data.display_name;
        setResolvedAddress(short);
        setAddress(short);
      }
    } catch {
      // Silent fail — coordinates are still set
    }
  }, []);

  async function handleAddressSearch() {
    if (!address.trim()) return;
    setSearching(true);
    setError('');
    try {
      const resp = await fetch(
        `${NOMINATIM_URL}/search?q=${encodeURIComponent(address)}&format=json&limit=1&accept-language=de`,
      );
      const results = await resp.json();
      if (results.length === 0) {
        setError('Adresse nicht gefunden. Versuch es mit Ort oder PLZ.');
        return;
      }
      const result = results[0];
      setLat(parseFloat(result.lat));
      setLon(parseFloat(result.lon));
      // Show the resolved name
      const name = result.display_name.split(', ').slice(0, 3).join(', ');
      setResolvedAddress(name);
    } catch {
      setError('Adresssuche fehlgeschlagen');
    } finally {
      setSearching(false);
    }
  }

  function handleGeolocate() {
    if (!('geolocation' in navigator)) {
      setError('GPS wird von deinem Browser nicht unterstuetzt');
      return;
    }
    setGeolocating(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const latitude = pos.coords.latitude;
        const longitude = pos.coords.longitude;
        setLat(latitude);
        setLon(longitude);
        await reverseGeocode(latitude, longitude);
        setGeolocating(false);
      },
      () => {
        setError('Standort konnte nicht ermittelt werden');
        setGeolocating(false);
      },
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (lat === null || lon === null) {
      setError('Bitte gib deine Adresse ein oder verwende GPS');
      return;
    }

    setLoading(true);
    try {
      await completeOnboarding({
        home_lat: lat,
        home_lon: lon,
        bike_name: bikeName || undefined,
        bike_type: bikeName ? bikeType : undefined,
      });
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Setup fehlgeschlagen');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 pt-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-white">Setup</h1>
        <p className="text-text-muted mt-2">Sag uns, wo du faehrst</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* Location */}
        <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
          <h2 className="font-semibold text-white">Standort</h2>

          {/* Address input */}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Adresse, Ort oder PLZ"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddressSearch(); } }}
              className="flex-1 px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-sm placeholder:text-text-muted focus:outline-none focus:border-accent-green"
            />
            <button
              type="button"
              onClick={handleAddressSearch}
              disabled={searching || !address.trim()}
              className="px-4 py-2.5 rounded-lg bg-accent-green/20 text-accent-green text-sm font-medium hover:bg-accent-green/30 transition-colors disabled:opacity-40"
            >
              {searching ? '...' : 'Suchen'}
            </button>
          </div>

          {/* GPS button */}
          <button
            type="button"
            onClick={handleGeolocate}
            disabled={geolocating}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-white/6 text-text-muted text-sm hover:bg-white/10 transition-colors disabled:opacity-40"
          >
            <span className="text-base">📍</span>
            {geolocating ? 'Standort wird ermittelt...' : 'Aktuellen Standort verwenden'}
          </button>

          {/* Resolved location display */}
          {lat !== null && lon !== null && (
            <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-accent-green/10 border border-accent-green/20">
              <span className="text-accent-green text-sm mt-0.5">✓</span>
              <div className="flex-1 min-w-0">
                {resolvedAddress && (
                  <p className="text-white text-sm font-medium truncate">{resolvedAddress}</p>
                )}
                <p className="text-text-muted text-xs">
                  {lat.toFixed(4)}, {lon.toFixed(4)}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Optional Bike */}
        <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
          <h2 className="font-semibold text-white">Erstes Bike <span className="text-text-muted font-normal text-sm">(optional)</span></h2>
          <input
            type="text"
            placeholder="Name (z.B. Trail Shredder)"
            value={bikeName}
            onChange={(e) => setBikeName(e.target.value)}
            className="w-full px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-sm placeholder:text-text-muted focus:outline-none focus:border-accent-green"
          />
          {bikeName && (
            <select
              value={bikeType}
              onChange={(e) => setBikeType(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-sm focus:outline-none focus:border-accent-green"
            >
              <option value="mtb">Mountainbike</option>
              <option value="emtb">E-Mountainbike</option>
              <option value="gravel">Gravel</option>
              <option value="road">Rennrad</option>
            </select>
          )}
        </div>

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading || lat === null}
          className="w-full py-3 rounded-xl bg-accent-green text-white font-semibold disabled:opacity-50 transition-opacity"
        >
          {loading ? 'Wird gespeichert...' : 'Los gehts!'}
        </button>
      </form>
    </div>
  );
}
