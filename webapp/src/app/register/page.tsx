'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

export default function RegisterPage() {
  const { user, register } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      router.replace(user.onboarding_done ? '/' : '/setup');
    }
  }, [user, router]);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen lang sein');
      return;
    }

    setLoading(true);
    try {
      await register(email, password, displayName);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registrierung fehlgeschlagen');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 pt-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-white">Konto erstellen</h1>
        <p className="text-text-muted mt-2">Werde Teil der TrailPilot-Community</p>
      </div>

      <form onSubmit={handleRegister} className="flex flex-col gap-4">
        <input
          type="text"
          placeholder="Anzeigename"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
          className="w-full px-4 py-3 rounded-xl bg-bg-card border border-border-card text-white placeholder:text-text-muted focus:outline-none focus:border-accent-green"
        />
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
          placeholder="Passwort (min. 8 Zeichen)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
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
          {loading ? 'Wird erstellt...' : 'Registrieren'}
        </button>
      </form>

      <p className="text-center text-text-muted text-sm">
        Bereits ein Konto?{' '}
        <Link href="/login" className="text-accent-green hover:underline">
          Anmelden
        </Link>
      </p>
    </div>
  );
}
