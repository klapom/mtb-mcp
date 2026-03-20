'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import type { TrainingGoal, TrainingPlan } from '@/lib/types';

// The /training/status endpoint may return CTL/ATL/TSB or a "no data" message
interface TrainingStatusResponse {
  has_data: boolean;
  message?: string;
  ctl?: number;
  atl?: number;
  tsb?: number;
  fitness_level?: string;
  trend?: string;
  active_goals?: { name: string; type: string; days_away: number }[];
}

function trendArrow(trend?: string): string {
  if (trend === 'up') return '\u2191';
  if (trend === 'down') return '\u2193';
  return '\u2192';
}

function fitnessVariant(level?: string): string {
  if (level === 'high' || level === 'peak') return 'green';
  if (level === 'moderate' || level === 'building') return 'orange';
  return 'gray';
}

function goalStatusVariant(status?: string): string {
  if (status === 'completed') return 'green';
  if (status === 'active' || status === 'in_progress') return 'blue';
  if (status === 'behind') return 'orange';
  return 'gray';
}

export default function TrainingPage() {
  const {
    data: status,
    error: statusError,
    isLoading: statusLoading,
    mutate: mutateStatus,
  } = useApi<TrainingStatusResponse>('/training/status');

  const {
    data: goals,
    error: goalsError,
    isLoading: goalsLoading,
    mutate: mutateGoals,
  } = useApi<TrainingGoal[]>('/training/goals');

  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null);

  const {
    data: plan,
    isLoading: planLoading,
  } = useApi<TrainingPlan>(selectedGoalId ? `/training/goals/${selectedGoalId}/plan` : null);

  if (statusLoading && goalsLoading) return <LoadingState text="Lade Training..." />;

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Training</h1>

      {/* Training Status */}
      {statusError ? (
        <ErrorState message={statusError.message} onRetry={() => mutateStatus()} />
      ) : statusLoading ? (
        <LoadingState text="Lade Fitness-Status..." />
      ) : status ? (
        <Card>
          <CardHeader
            title="Fitness-Status"
            action={
              status.has_data && status.fitness_level ? (
                <div className="flex items-center gap-2">
                  <Badge variant={fitnessVariant(status.fitness_level)}>
                    {status.fitness_level}
                  </Badge>
                  <span className="text-lg">{trendArrow(status.trend)}</span>
                </div>
              ) : undefined
            }
          />
          {status.has_data && status.ctl != null ? (
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-xs text-text-muted uppercase tracking-wider mb-1">CTL</p>
                <p className="text-xl font-bold text-accent-green">{status.ctl.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-text-muted uppercase tracking-wider mb-1">ATL</p>
                <p className="text-xl font-bold text-accent-orange">{(status.atl ?? 0).toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-text-muted uppercase tracking-wider mb-1">TSB</p>
                <p
                  className={`text-xl font-bold ${
                    (status.tsb ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red'
                  }`}
                >
                  {(status.tsb ?? 0) >= 0 ? '+' : ''}
                  {(status.tsb ?? 0).toFixed(1)}
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-sm text-text-muted">{status.message ?? 'Noch keine Fitness-Daten'}</p>
              {status.active_goals && status.active_goals.length > 0 && (
                <div className="mt-3 space-y-1">
                  {status.active_goals.map((g) => (
                    <p key={g.name} className="text-xs text-text-secondary">
                      {g.name} ({g.type}) — in {g.days_away} Tagen
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      ) : null}

      {/* Active Goals */}
      {goalsError ? (
        <ErrorState message={goalsError.message} onRetry={() => mutateGoals()} />
      ) : goalsLoading ? (
        <LoadingState text="Lade Ziele..." />
      ) : (
        <div>
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-2">
            Aktive Ziele
          </h2>

          {!goals || goals.length === 0 ? (
            <Card>
              <p className="text-sm text-text-muted text-center py-4">
                Kein aktives Ziel
              </p>
            </Card>
          ) : (
            <div className="space-y-3">
              {goals.map((goal) => (
                <Card
                  key={goal.id}
                  className={`cursor-pointer ${
                    selectedGoalId === goal.id ? 'border-accent-green' : ''
                  }`}
                >
                  <div
                    onClick={() =>
                      setSelectedGoalId(selectedGoalId === goal.id ? null : goal.id)
                    }
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{goal.name}</span>
                      <Badge variant={goalStatusVariant(goal.status)}>
                        {goal.status ?? goal.goal_type ?? 'active'}
                      </Badge>
                    </div>
                    <div className="flex gap-4 text-xs text-text-muted">
                      {goal.target_date && <span>Ziel: {goal.target_date}</span>}
                      {goal.goal_type && <span>{goal.goal_type}</span>}
                    </div>
                    {goal.progress_pct != null && (
                      <div className="flex items-center gap-2 mt-2">
                        <div className="flex-1">
                          <div className="w-full h-1.5 bg-white/8 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full progress-green"
                              style={{ width: `${goal.progress_pct}%` }}
                            />
                          </div>
                        </div>
                        <span className="text-xs text-text-secondary font-medium">
                          {goal.progress_pct}%
                        </span>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Training Plan for Selected Goal */}
      {selectedGoalId && (
        <div className="mt-4">
          {planLoading ? (
            <LoadingState text="Lade Trainingsplan..." />
          ) : plan && plan.weeks && plan.weeks.length > 0 ? (
            <Card>
              <CardHeader title="Trainingsplan" />
              <div className="space-y-4">
                {plan.weeks.map((week) => (
                  <div key={week.week_number}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold">
                        Woche {week.week_number}
                      </span>
                      <Badge variant="gray">{week.phase}</Badge>
                    </div>
                    <p className="text-xs text-text-muted mb-2">
                      {week.target_hours}h / {week.target_tss} TSS
                    </p>
                    <div className="space-y-1">
                      {week.sessions.map((session, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-xs bg-white/5 rounded-lg px-3 py-2"
                        >
                          <span className="text-text-secondary">{session.day}</span>
                          <span className="font-medium">{session.type}</span>
                          <span className="text-text-muted">
                            {session.duration_min} min
                          </span>
                          <Badge
                            variant={
                              session.intensity === 'high'
                                ? 'red'
                                : session.intensity === 'medium'
                                  ? 'orange'
                                  : 'green'
                            }
                          >
                            {session.intensity}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <Card>
              <p className="text-sm text-text-muted text-center py-4">
                Kein Plan vorhanden
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
