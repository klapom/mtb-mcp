'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Auth } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';

function ProfileContent() {
  const { user, updateProfile, logout } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [inviteToken, setInviteToken] = useState('');

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name);
      setLat(user.home_lat?.toString() ?? '');
      setLon(user.home_lon?.toString() ?? '');
    }
  }, [user]);

  async function handleSave() {
    setSaving(true);
    setMessage('');
    try {
      await updateProfile({
        display_name: displayName,
        home_lat: lat ? parseFloat(lat) : undefined,
        home_lon: lon ? parseFloat(lon) : undefined,
      });
      setMessage('Profil gespeichert');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  }

  async function handleStravaConnect() {
    try {
      const data = await Auth.stravaAuthorize();
      // Mark this as a "connect" flow so the callback knows
      localStorage.setItem('strava_flow', 'connect');
      window.location.href = data.authorize_url;
    } catch {
      setMessage('Strava-Verbindung fehlgeschlagen');
    }
  }

  async function handleCreateInvite() {
    try {
      const token = localStorage.getItem('trailpilot_token');
      const resp = await fetch(
        `http://${window.location.hostname}:8001/api/v1/trainer/invite`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        },
      );
      const json = await resp.json();
      if (json.status === 'ok') {
        setInviteToken(json.data.token);
      }
    } catch {
      setMessage('Fehler beim Erstellen des Einladungslinks');
    }
  }

  function handleLogout() {
    logout();
    router.replace('/login');
  }

  if (!user) return null;

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-xl font-bold text-white">Profil</h1>

      {/* User Info */}
      <div className="bg-bg-card rounded-xl border border-border-card p-4 flex items-center gap-3">
        {user.avatar_url ? (
          <img src={user.avatar_url} alt="" className="w-12 h-12 rounded-full" />
        ) : (
          <div className="w-12 h-12 rounded-full bg-accent-green/20 flex items-center justify-center text-accent-green font-bold text-lg">
            {user.display_name[0]?.toUpperCase()}
          </div>
        )}
        <div>
          <p className="text-white font-semibold">{user.display_name}</p>
          <p className="text-text-muted text-sm">{user.email ?? 'Strava-Konto'}</p>
        </div>
      </div>

      {/* Edit Profile */}
      <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
        <h2 className="font-semibold text-white text-sm">Profil bearbeiten</h2>
        <input
          type="text"
          placeholder="Anzeigename"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="w-full px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-sm placeholder:text-text-muted focus:outline-none focus:border-accent-green"
        />
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Breitengrad"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            className="flex-1 px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-sm placeholder:text-text-muted focus:outline-none focus:border-accent-green"
          />
          <input
            type="text"
            placeholder="Laengengrad"
            value={lon}
            onChange={(e) => setLon(e.target.value)}
            className="flex-1 px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-sm placeholder:text-text-muted focus:outline-none focus:border-accent-green"
          />
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-2.5 rounded-lg bg-accent-green text-white text-sm font-semibold disabled:opacity-50"
        >
          {saving ? 'Speichern...' : 'Speichern'}
        </button>
      </div>

      {/* Strava */}
      <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
        <h2 className="font-semibold text-white text-sm">Strava</h2>
        {user.strava_connected ? (
          <p className="text-accent-green text-sm">Verbunden (Athlete #{user.strava_athlete_id})</p>
        ) : (
          <button
            onClick={handleStravaConnect}
            className="w-full py-2.5 rounded-lg text-white text-sm font-semibold"
            style={{ backgroundColor: '#FC4C02' }}
          >
            Mit Strava verbinden
          </button>
        )}
      </div>

      {/* Trainer Invite */}
      <div className="bg-bg-card rounded-xl border border-border-card p-4 flex flex-col gap-3">
        <h2 className="font-semibold text-white text-sm">Trainer einladen</h2>
        <p className="text-text-muted text-xs">
          Erstelle einen Einladungslink, damit dein Trainer deine Fitness-Daten sehen kann.
        </p>
        {inviteToken ? (
          <div className="flex flex-col gap-2">
            <input
              readOnly
              value={`${window.location.origin}/trainer/accept?token=${inviteToken}`}
              className="w-full px-3 py-2.5 rounded-lg bg-bg-primary border border-border-subtle text-white text-xs font-mono"
              onClick={(e) => (e.target as HTMLInputElement).select()}
            />
            <button
              onClick={() => navigator.clipboard.writeText(`${window.location.origin}/trainer/accept?token=${inviteToken}`)}
              className="text-accent-green text-xs"
            >
              Link kopieren
            </button>
          </div>
        ) : (
          <button
            onClick={handleCreateInvite}
            className="w-full py-2.5 rounded-lg bg-white/10 text-white text-sm font-semibold hover:bg-white/15"
          >
            Einladungslink erstellen
          </button>
        )}
      </div>

      {message && (
        <p className={`text-sm text-center ${message.includes('Fehler') ? 'text-red-400' : 'text-accent-green'}`}>
          {message}
        </p>
      )}

      {/* Logout */}
      <button
        onClick={handleLogout}
        className="w-full py-2.5 rounded-xl border border-red-500/30 text-red-400 text-sm font-semibold hover:bg-red-500/10 transition-colors"
      >
        Abmelden
      </button>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}
