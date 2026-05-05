// This project was developed with assistance from AI tools.

import type { CustomerImpact } from "../types/events";

interface Props {
  impact: CustomerImpact | null;
}

export function CustomerImpactBanner({ impact }: Props) {
  if (!impact || impact.total_affected === 0) return null;

  const restored = impact.restored > 0;
  const fullyRestored = restored && impact.remaining === 0;
  const stateClass = fullyRestored ? "grid-impact-banner--restored" : restored ? "grid-impact-banner--partial" : "";
  const className = `grid-impact-banner grid-impact-banner--active ${stateClass}`;

  return (
    <div className={className}>
      <strong>{impact.total_affected.toLocaleString()} customers affected</strong>
      {restored ? (
        <>
          <span>⬤ {impact.restored.toLocaleString()} restored</span>
          <span>⬤ {impact.remaining.toLocaleString()} remaining</span>
          {impact.etr_minutes != null && impact.etr_minutes > 0 && (
            <span className="grid-mono">ETR: {Math.floor(impact.etr_minutes / 60)}h {impact.etr_minutes % 60}m</span>
          )}
        </>
      ) : (
        <span>0 restored</span>
      )}
    </div>
  );
}
