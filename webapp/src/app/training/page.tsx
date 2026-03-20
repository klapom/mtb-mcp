'use client';

import { useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { ProgressBar } from '@/components/ui/ProgressBar';
import type { TrainingStatus, TrainingGoal, TrainingPlan } from '@/lib/types';

function trendArrow(trend: string): string {
  if (trend === 'up') return '\u2191';
  if (trend === 'down') return '\u2193';
  return '\u2192';
}

function fitnessVariant(level: string): string {
  if (level === 'high' || level === 'peak') return 'green';
  if (level === 'moderate' || level === 'building') return 'orange';
  return 'red';
}

function goalStatusVariant(status: string): string {
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
  } = useApi<TrainingStatus>('/training/fitness');

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
    <div className="p-4 pb-[calc(16px+var(--nav-height))]">
      <h1 className="text-lg font-bold mb-3">Training</h1>

      {/* Training Status */}
      {statusError ? (
        <ErrorState message={statusError.message} onRetry={() => mutateStatus()} />
      ) : statusLoading ? (
        <LoadingState text="Lade Fitness-Status..." />
      ) : status ? (
        <Card className="mb-4">
          <CardHeader
            title="Fitness-Status"
            action={
              <div className="flex items-center gap-2">
                <Badge variant={fitnessVariant(status.fitness_level)}>
                  {status.fitness_level}
                </Badge>
                <span className="text-lg">{trendArrow(status.trend)}</span>
              </div>
            }
          />
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">CTL</p>
              <p className="text-xl font-bold text-accent-green">{status.ctl.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">ATL</p>
              <p className="text-xl font-bold text-accent-orange">{status.atl.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wider mb-1">TSB</p>
              <p
                className={`text-xl font-bold ${
                  status.tsb >= 0 ? 'text-accent-green' : 'text-accent-red'
                }`}
              >
                {status.tsb >= 0 ? '+' : ''}
                {status.tsb.toFixed(1)}
              </p>
            </div>
          </div>
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
                        {goal.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-text-muted mb-2">
                      Ziel: {goal.target_date}
                    </p>
                    <div className="flex items-center gap-2">
                      <ProgressBar pct={goal.progress_pct} className="flex-1" />
                      <span className="text-xs text-text-secondary font-medium">
                        {goal.progress_pct}%
                      </span>
                    </div>
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
          ) : plan && plan.weeks.length > 0 ? (
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
