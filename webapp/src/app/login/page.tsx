'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { Auth } from '@/lib/api';

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      router.replace(user.onboarding_done ? '/' : '/setup');
    }
  }, [user, router]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login fehlgeschlagen');
    } finally {
      setLoading(false);
    }
  }

  async function handleStravaLogin() {
    try {
      const data = await Auth.stravaAuthorize();
      window.location.href = data.authorize_url;
    } catch {
      setError('Strava-Verbindung fehlgeschlagen');
    }
  }

  return (
    <div className="flex flex-col gap-6 pt-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-white">Willkommen bei TrailPilot</h1>
        <p className="text-text-muted mt-2">Melde dich an, um loszulegen</p>
      </div>

      {/* Strava OAuth */}
      <button
        onClick={handleStravaLogin}
        className="w-full py-3 px-4 rounded-xl font-semibold text-white flex items-center justify-center gap-2"
        style={{ backgroundColor: '#FC4C02' }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
          <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169" />
        </svg>
        Mit Strava anmelden
      </button>

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-border-subtle" />
        <span className="text-text-muted text-sm">oder</span>
        <div className="flex-1 h-px bg-border-subtle" />
      </div>

      {/* Email/PW Login */}
      <form onSubmit={handleLogin} className="flex flex-col gap-4">
        <input
          type="email"
          placeholder="E-Mail"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-4 py-3 rounded-xl bg-bg-card border border-border-card text-white placeholder:text-text-muted focus:outline-none focus:border-accent-green"
        />
        <input
          type="password"
          placeholder="Passwort"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full px-4 py-3 rounded-xl bg-bg-card border border-border-card text-white placeholder:text-text-muted focus:outline-none focus:border-accent-green"
        />

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-accent-green text-white font-semibold disabled:opacity-50 transition-opacity"
        >
          {loading ? 'Anmelden...' : 'Anmelden'}
        </button>
      </form>

      <p className="text-center text-text-muted text-sm">
        Noch kein Konto?{' '}
        <Link href="/register" className="text-accent-green hover:underline">
          Registrieren
        </Link>
      </p>
    </div>
  );
}
