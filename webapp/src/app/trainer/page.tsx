'use client';

import Link from 'next/link';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useApi } from '@/hooks/useApi';

interface Athlete {
  id: string;
  display_name: string;
  avatar_url: string | null;
}

function TrainerContent() {
  const { data: athletes, isLoading, error } = useApi<Athlete[]>('/trainer/athletes');

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-xl font-bold text-white">Meine Athleten</h1>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-accent-green border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="bg-bg-card rounded-xl border border-border-card p-4 text-center">
          <p className="text-text-muted text-sm">Keine Athleten gefunden</p>
          <p className="text-text-muted text-xs mt-1">
            Athleten koennen dich ueber einen Einladungslink als Trainer hinzufuegen.
          </p>
        </div>
      )}

      {athletes && athletes.length === 0 && (
        <div className="bg-bg-card rounded-xl border border-border-card p-6 text-center">
          <p className="text-text-muted">Noch keine Athleten</p>
          <p className="text-text-muted text-xs mt-2">
            Deine Athleten koennen dich ueber ihren Profil-Einladungslink hinzufuegen.
          </p>
        </div>
      )}

      {athletes && athletes.length > 0 && (
        <div className="flex flex-col gap-3">
          {athletes.map((athlete) => (
            <Link
              key={athlete.id}
              href={`/trainer/${athlete.id}`}
              className="bg-bg-card rounded-xl border border-border-card p-4 flex items-center gap-3 hover:border-accent-green/30 transition-colors"
            >
              {athlete.avatar_url ? (
                <img src={athlete.avatar_url} alt="" className="w-10 h-10 rounded-full" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-accent-green/20 flex items-center justify-center text-accent-green font-bold">
                  {athlete.display_name[0]?.toUpperCase()}
                </div>
              )}
              <div className="flex-1">
                <p className="text-white font-medium">{athlete.display_name}</p>
              </div>
              <span className="text-text-muted text-lg">&rsaquo;</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TrainerPage() {
  return (
    <ProtectedRoute>
      <TrainerContent />
    </ProtectedRoute>
  );
}
