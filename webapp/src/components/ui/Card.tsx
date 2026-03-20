import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`bg-bg-card border border-border-card rounded-xl p-4 shadow-[0_2px_12px_rgba(0,0,0,0.3)] transition-shadow hover:shadow-[0_4px_16px_rgba(0,0,0,0.35)] ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  action,
}: {
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-[13px] font-semibold uppercase tracking-wider text-text-secondary">
        {title}
      </h3>
      {action}
    </div>
  );
}
