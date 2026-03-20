'use client';

import { useState } from 'react';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { EBike } from '@/lib/api';
import type { RangeCheckResult } from '@/lib/types';

export default function EBikePage() {
  const [batteryWh, setBatteryWh] = useState(625);
  const [batteryPct, setBatteryPct] = useState(100);
  const [distanceKm, setDistanceKm] = useState('');
  const [elevationGain, setElevationGain] = useState('');
  const [riderWeight, setRiderWeight] = useState(80);

  const [result, setResult] = useState<RangeCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!distanceKm || !elevationGain) return;
    setLoading(true);
    setError(null);
    try {
      const data = await EBike.rangeCheck({
        battery_wh: batteryWh,
        battery_pct: batteryPct,
        distance_km: Number(distanceKm),
        elevation_gain_m: Number(elevationGain),
        rider_weight_kg: riderWeight,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Berechnung fehlgeschlagen');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-4 pb-[calc(16px+var(--nav-height))]">
      <h1 className="text-lg font-bold mb-3">eBike Range Check</h1>

      {/* Input Form */}
      <Card className="mb-4">
        <CardHeader title="Parameter" />
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Akku (Wh)
            </label>
            <input
              type="number"
              value={batteryWh}
              onChange={(e) => setBatteryWh(Number(e.target.value))}
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Ladestand ({batteryPct}%)
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={batteryPct}
              onChange={(e) => setBatteryPct(Number(e.target.value))}
              className="w-full accent-accent-green"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Distanz (km)
            </label>
            <input
              type="number"
              value={distanceKm}
              onChange={(e) => setDistanceKm(e.target.value)}
              placeholder="z.B. 45"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              H&ouml;henmeter (m)
            </label>
            <input
              type="number"
              value={elevationGain}
              onChange={(e) => setElevationGain(e.target.value)}
              placeholder="z.B. 1200"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Fahrergewicht (kg)
            </label>
            <input
              type="number"
              value={riderWeight}
              onChange={(e) => setRiderWeight(Number(e.target.value))}
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading || !distanceKm || !elevationGain}
            className="w-full bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold disabled:opacity-40"
          >
            {loading ? 'Berechne...' : 'Berechnen'}
          </button>
        </div>
      </Card>

      {error && (
        <Card className="mb-4">
          <p className="text-sm text-accent-red text-center py-2">{error}</p>
        </Card>
      )}

      {/* Result Card */}
      {result && (
        <Card>
          <CardHeader
            title="Ergebnis"
            action={
              <Badge variant={result.feasible ? 'green' : 'red'}>
                {result.feasible ? 'Machbar' : 'Nicht machbar'}
              </Badge>
            }
          />

          <p className="text-sm text-text-secondary mb-4">{result.verdict}</p>

          <div className="grid grid-cols-3 gap-3 text-center mb-4">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Reichweite
              </p>
              <p className="text-lg font-bold">{result.estimated_range_km} km</p>
            </div>
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                Route
              </p>
              <p className="text-lg font-bold">{result.route_distance_km} km</p>
            </div>
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
                H&ouml;henmeter
              </p>
              <p className="text-lg font-bold">{result.elevation_gain_m} m</p>
            </div>
          </div>

          <div className="mb-4">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-text-secondary">Akku am Ziel</span>
              <span className="font-semibold">{result.battery_at_finish_pct}%</span>
            </div>
            <ProgressBar pct={result.battery_at_finish_pct} />
          </div>

          {/* Modes Comparison Table */}
          {result.modes.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">
                Modi-Vergleich
              </h3>
              <div className="bg-white/5 rounded-lg overflow-hidden">
                <div className="grid grid-cols-3 gap-2 px-3 py-2 text-xs font-semibold text-text-muted uppercase tracking-wider border-b border-border-subtle">
                  <span>Modus</span>
                  <span className="text-right">Reichweite</span>
                  <span className="text-right">Akku</span>
                </div>
                {result.modes.map((mode) => (
                  <div
                    key={mode.mode}
                    className="grid grid-cols-3 gap-2 px-3 py-2 text-sm border-b border-border-subtle last:border-0"
                  >
                    <span className="font-medium">{mode.mode}</span>
                    <span className="text-right text-text-secondary">
                      {mode.range_km} km
                    </span>
                    <span className="text-right text-text-secondary">
                      {mode.battery_pct}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
