export function ProgressBar({
  pct,
  className = "",
}: {
  pct: number;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  const colorClass =
    clamped < 60 ? "progress-green" : clamped < 85 ? "progress-yellow" : "progress-red";

  return (
    <div className={`w-full h-1.5 bg-white/8 rounded-full overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full transition-[width] duration-800 ${colorClass}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
