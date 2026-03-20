import { ProgressBar } from "@/components/ui/ProgressBar";
import type { BikeComponent } from "@/lib/types";

export function ComponentWearBar({ component }: { component: BikeComponent }) {
  return (
    <div className="py-2" data-testid="component-wear">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium">{component.component_type}</span>
        <span className="text-xs text-text-secondary">
          {component.wear_pct}%
        </span>
      </div>
      <ProgressBar pct={component.wear_pct} />
      <div className="flex justify-between mt-1 text-xs text-text-muted">
        <span>
          {component.brand} {component.model}
        </span>
        <span>
          {component.current_km}/{component.max_km} km
        </span>
      </div>
    </div>
  );
}
