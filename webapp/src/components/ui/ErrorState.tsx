"use client";

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
      <span className="text-3xl">⚠️</span>
      <p className="text-sm text-text-secondary">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-4 py-2 bg-accent-green text-white text-sm font-semibold rounded-lg hover:bg-[#0db365] transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}
