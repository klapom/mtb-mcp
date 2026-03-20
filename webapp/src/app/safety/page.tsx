'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Modal } from '@/components/ui/Modal';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Safety } from '@/lib/api';
import type { SafetyTimer } from '@/lib/types';

export default function SafetyPage() {
  const { data: timer, error, isLoading, mutate } = useApi<SafetyTimer>('/safety/timer');

  const [showNewTimer, setShowNewTimer] = useState(false);
  const [duration, setDuration] = useState('');
  const [description, setDescription] = useState('');
  const [emergencyContact, setEmergencyContact] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleStartTimer() {
    if (!duration || !description) return;
    setSubmitting(true);
    try {
      await Safety.startTimer({
        duration_minutes: Number(duration),
        ride_description: description,
        emergency_contact: emergencyContact || undefined,
      });
      setShowNewTimer(false);
      setDuration('');
      setDescription('');
      setEmergencyContact('');
      mutate();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    if (!timer) return;
    await Safety.cancelTimer(timer.timer_id);
    mutate();
  }

  if (isLoading) return <LoadingState text="Lade Timer..." />;
  if (error) return <ErrorState message={error.message} onRetry={() => mutate()} />;

  const isActive = timer && timer.status === 'active';

  // Calculate progress as time elapsed out of total duration
  function getTimerProgressPct(): number {
    if (!timer) return 0;
    const started = new Date(timer.started_at).getTime();
    const expires = new Date(timer.expires_at).getTime();
    const totalMinutes = (expires - started) / 60000;
    if (totalMinutes <= 0) return 100;
    return Math.max(0, Math.min(100, ((totalMinutes - timer.remaining_minutes) / totalMinutes) * 100));
  }

  function getTotalMinutes(): number {
    if (!timer) return 0;
    const started = new Date(timer.started_at).getTime();
    const expires = new Date(timer.expires_at).getTime();
    return Math.round((expires - started) / 60000);
  }

  return (
    <div className="p-4 pb-[calc(16px+var(--nav-height))]">
      <h1 className="text-lg font-bold mb-3">Sicherheits-Timer</h1>

      {isActive ? (
        <Card>
          <CardHeader
            title="Aktiver Timer"
            action={<Badge variant="green">aktiv</Badge>}
          />

          <div className="text-center mb-4">
            <p className="text-4xl font-bold text-accent-green">
              {timer.remaining_minutes} min
            </p>
            <p className="text-sm text-text-muted mt-1">verbleibend</p>
          </div>

          <p className="text-sm text-text-secondary mb-4 text-center">
            {timer.ride_description}
          </p>

          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-text-muted mb-1">
              <span>Fortschritt</span>
              <span>
                {timer.remaining_minutes} / {getTotalMinutes()} min
              </span>
            </div>
            <ProgressBar pct={getTimerProgressPct()} />
          </div>

          {timer.emergency_contact && (
            <p className="text-xs text-text-muted mb-4">
              Notfallkontakt: {timer.emergency_contact}
            </p>
          )}

          <button
            onClick={handleCancel}
            className="w-full bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold"
          >
            Entwarnung
          </button>
        </Card>
      ) : (
        <Card>
          <div className="text-center py-8">
            <p className="text-sm text-text-muted mb-4">Kein aktiver Timer</p>
            <button
              onClick={() => setShowNewTimer(true)}
              className="bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold"
            >
              Neuer Timer
            </button>
          </div>
        </Card>
      )}

      {/* Neuer Timer Modal */}
      <Modal
        open={showNewTimer}
        onClose={() => {
          setShowNewTimer(false);
          setDuration('');
          setDescription('');
          setEmergencyContact('');
        }}
        title="Neuer Timer"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Dauer (Minuten) *
            </label>
            <input
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              placeholder="z.B. 120"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Beschreibung *
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="z.B. Trail-Runde Frankenjura"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
              Notfallkontakt
            </label>
            <input
              type="text"
              value={emergencyContact}
              onChange={(e) => setEmergencyContact(e.target.value)}
              placeholder="optional, z.B. +49 170 1234567"
              className="w-full p-2.5 bg-bg-input border border-border-card rounded-lg text-sm text-text-primary focus:border-accent-green outline-none"
            />
          </div>
          <button
            onClick={handleStartTimer}
            disabled={submitting || !duration || !description}
            className="w-full bg-accent-green text-white px-5 py-2.5 rounded-lg font-semibold disabled:opacity-40"
          >
            {submitting ? 'Starte...' : 'Timer starten'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
