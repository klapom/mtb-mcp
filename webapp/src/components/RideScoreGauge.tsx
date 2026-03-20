function scoreColor(score: number): string {
  if (score >= 80) return "#4caf50";
  if (score >= 60) return "#ff9800";
  if (score >= 40) return "#f39c12";
  return "#e74c3c";
}

function scoreVerdict(score: number): string {
  if (score >= 80) return "Great";
  if (score >= 60) return "Good";
  if (score >= 40) return "Fair";
  return "Poor";
}

export function RideScoreGauge({
  score,
  verdict,
}: {
  score: number;
  verdict?: string;
}) {
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const offset = circumference - progress;
  const color = scoreColor(score);

  return (
    <div className="relative w-[140px] h-[140px] mx-auto">
      <svg width="140" height="140" className="rotate-[-90deg]">
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="8"
        />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="gauge-fill"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-3xl font-bold"
          data-testid="ride-score-value"
          style={{ color }}
        >
          {score}
        </span>
        <span className="text-xs text-text-secondary">
          {verdict ?? scoreVerdict(score)}
        </span>
      </div>
    </div>
  );
}
