'use client';

import { Suspense, useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

function CallbackInner() {
  const { loginWithStrava, connectStrava, user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState('');
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const code = searchParams.get('code');
    if (!code) {
      setError('Kein Autorisierungscode von Strava erhalten');
      return;
    }

    // Check if this is a "connect" flow (user already logged in)
    const flow = localStorage.getItem('strava_flow');
    localStorage.removeItem('strava_flow');

    if (flow === 'connect') {
      // Connect Strava to existing account
      connectStrava(code)
        .then(() => router.replace('/profile'))
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Strava-Verbindung fehlgeschlagen');
        });
    } else {
      // Login/signup via Strava
      loginWithStrava(code)
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Strava-Anmeldung fehlgeschlagen');
        });
    }
  }, [searchParams, loginWithStrava, connectStrava, router]);

  useEffect(() => {
    // Only redirect for login flow (not connect flow)
    const flow = localStorage.getItem('strava_flow');
    if (user && flow !== 'connect') {
      router.replace(user.onboarding_done ? '/' : '/setup');
    }
  }, [user, router]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-red-400">{error}</p>
        <button
          onClick={() => router.push('/profile')}
          className="px-6 py-2 rounded-xl bg-accent-green text-white font-semibold"
        >
          Zurueck zum Profil
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
      <div className="w-8 h-8 border-2 border-accent-green border-t-transparent rounded-full animate-spin" />
      <p className="text-text-muted">Strava-Verbindung wird hergestellt...</p>
    </div>
  );
}

export default function StravaCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
          <div className="w-8 h-8 border-2 border-accent-green border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <CallbackInner />
    </Suspense>
  );
}
