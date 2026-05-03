// This project was developed with assistance from AI tools.

import type { CustomerImpact } from "../types/events";

interface Props {
  impact: CustomerImpact | null;
}

export function CustomerImpactBanner({ impact }: Props) {
  if (!impact || impact.total_affected === 0) return null;

  const restored = impact.restored > 0;
  const className = `grid-impact-banner grid-impact-banner--active ${restored ? "grid-impact-banner--restored" : ""}`;

  return (
    <div className={className}>
      <strong>{impact.total_affected.toLocaleString()} customers affected</strong>
      {impact.restored > 0 && (
        <span>{impact.restored.toLocaleString()} restored via automatic switching</span>
      )}
      {impact.remaining > 0 && (
        <span>{impact.remaining.toLocaleString()} remaining</span>
      )}
      {impact.etr_minutes && (
        <span className="grid-mono">ETR: {Math.floor(impact.etr_minutes / 60)}h {impact.etr_minutes % 60}m</span>
      )}
    </div>
  );
}
