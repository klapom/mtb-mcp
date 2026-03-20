export function LoadingState({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <div className="w-8 h-8 border-2 border-accent-green border-t-transparent rounded-full animate-spin" />
      <span className="text-sm text-text-secondary">{text}</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`bg-white/5 rounded-lg animate-pulse ${className}`}
    />
  );
}
