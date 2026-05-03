// This project was developed with assistance from AI tools.

import type { AssetRiskScore } from "../types/events";

interface RiskTableProps {
  riskScores: Map<string, AssetRiskScore>;
}

function badgeClass(score: number): string {
  if (score >= 0.85) return "grid-risk-badge grid-risk-badge--critical";
  if (score >= 0.65) return "grid-risk-badge grid-risk-badge--high";
  if (score >= 0.40) return "grid-risk-badge grid-risk-badge--medium";
  return "grid-risk-badge grid-risk-badge--low";
}

function fmt(n: number): string {
  return n.toFixed(2);
}

export function RiskTable({ riskScores }: RiskTableProps) {
  const sorted = Array.from(riskScores.values())
    .sort((a, b) => b.composite_score - a.composite_score)
    .slice(0, 20);

  return (
    <div className="grid-card">
      <div className="grid-card__header">Asset Risk Rankings</div>
      <div className="grid-card__body--flush" style={{ maxHeight: 280, overflowY: "auto" }}>
        <table className="grid-risk-table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Type</th>
              <th>Score</th>
              <th>Wx</th>
              <th>Age</th>
              <th>Veg</th>
              <th>Insp</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} style={{ color: "#6A6E73", textAlign: "center", padding: 12 }}>
                  No risk data
                </td>
              </tr>
            )}
            {sorted.map((r) => (
              <tr key={r.asset_id}>
                <td className="grid-mono">{r.asset_id}</td>
                <td>{r.asset_type}</td>
                <td>
                  <span className={badgeClass(r.composite_score)}>{fmt(r.composite_score)}</span>
                </td>
                <td>{fmt(r.breakdown.weather_exposure)}</td>
                <td>{fmt(r.breakdown.age)}</td>
                <td>{fmt(r.breakdown.vegetation)}</td>
                <td>{fmt(r.breakdown.inspection_recency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
