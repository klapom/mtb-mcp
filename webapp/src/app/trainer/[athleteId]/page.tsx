'use client';

import { use } from 'react';
import Link from 'next/link';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useApi } from '@/hooks/useApi';

interface FitnessData {
  has_data: boolean;
  ctl?: number;
  atl?: number;
  tsb?: number;
  weekly_km?: number;
  weekly_elevation_m?: number;
  weekly_hours?: number;
  weekly_rides?: number;
}

interface Goal {
  id: string;
  name: string;
  type: string;
  target_date: string;
  status: string;
}

function AthleteContent({ athleteId }: { athleteId: string }) {
  const { data: fitness, isLoading: fitnessLoading } = useApi<FitnessData>(
    `/trainer/athletes/${athleteId}/fitness`,
  );
  const { data: goals, isLoading: goalsLoading } = useApi<Goal[]>(
    `/trainer/athletes/${athleteId}/goals`,
  );

  const isLoading = fitnessLoading || goalsLoading;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <Link href="/trainer" className="text-text-muted hover:text-white text-sm">
          &lsaquo; Athleten
        </Link>
      </div>

      <h1 className="text-xl font-bold text-white">Athleten-Dashboard</h1>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-green border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Fitness */}
      {fitness && (
        <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
          <h2 className="font-semibold text-white text-sm">Fitness</h2>
          {!fitness.has_data ? (
            <p className="text-text-muted text-sm">Keine Fitnessdaten vorhanden</p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-bg-primary rounded-lg p-3">
                <p className="text-text-muted text-xs">CTL</p>
                <p className="text-white text-lg font-bold">{fitness.ctl?.toFixed(1)}</p>
              </div>
              <div className="bg-bg-primary rounded-lg p-3">
                <p className="text-text-muted text-xs">ATL</p>
                <p className="text-white text-lg font-bold">{fitness.atl?.toFixed(1)}</p>
              </div>
              <div className="bg-bg-primary rounded-lg p-3">
                <p className="text-text-muted text-xs">TSB</p>
                <p className={`text-lg font-bold ${(fitness.tsb ?? 0) >= 0 ? 'text-accent-green' : 'text-red-400'}`}>
                  {fitness.tsb?.toFixed(1)}
                </p>
              </div>
              <div className="bg-bg-primary rounded-lg p-3">
                <p className="text-text-muted text-xs">Woche</p>
                <p className="text-white text-lg font-bold">{fitness.weekly_rides} Fahrten</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Goals */}
      {goals && (
        <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
          <h2 className="font-semibold text-white text-sm">Trainingsziele</h2>
          {goals.length === 0 ? (
            <p className="text-text-muted text-sm">Keine aktiven Ziele</p>
          ) : (
            <div className="flex flex-col gap-2">
              {goals.map((goal) => (
                <div key={goal.id} className="bg-bg-primary rounded-lg p-3 flex justify-between items-center">
                  <div>
                    <p className="text-white text-sm font-medium">{goal.name}</p>
                    <p className="text-text-muted text-xs">{goal.type} &middot; {goal.target_date}</p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded bg-accent-green/20 text-accent-green">
                    {goal.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AthletePage({ params }: { params: Promise<{ athleteId: string }> }) {
  const { athleteId } = use(params);
  return (
    <ProtectedRoute>
      <AthleteContent athleteId={athleteId} />
    </ProtectedRoute>
  );
}
