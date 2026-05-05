// This project was developed with assistance from AI tools.

import type { AssetRiskScore } from "../types/events";

interface TriageOverlayProps {
  active: boolean;
  riskScores: Map<string, AssetRiskScore>;
  onClose: () => void;
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

const COLUMNS = [
  { key: "wx", label: "WX", desc: "Weather exposure from the CorrDiff forecast — wind speed and ice accumulation at this location" },
  { key: "age", label: "AGE", desc: "How close the asset is to end of expected service life" },
  { key: "veg", label: "VEG", desc: "Proximity of vegetation to conductors — closer means higher risk of contact" },
  { key: "insp", label: "INSP", desc: "Time since last inspection — longer gaps increase uncertainty" },
];

export function TriageOverlay({ active, riskScores, onClose }: TriageOverlayProps) {
  if (!active) return null;

  const sorted = Array.from(riskScores.values())
    .sort((a, b) => b.composite_score - a.composite_score)
    .slice(0, 10);

  return (
    <div style={{
      position: "absolute",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      zIndex: 999,
      background: "rgba(21,21,21,0.94)",
      borderRadius: 6,
      border: "1px solid rgba(255,255,255,0.1)",
      padding: "16px 20px 14px",
      color: "#fff",
      fontFamily: "Inter, sans-serif",
      backdropFilter: "blur(8px)",
      boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
      maxWidth: "90%",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "rgba(255,255,255,0.6)" }}>
          AI Risk Assessment
        </span>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 0 }}
        >
          ×
        </button>
      </div>

      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", marginBottom: 14, lineHeight: 1.5, maxWidth: 620 }}>
        Each asset is scored across four risk dimensions. The composite score determines monitoring priority — highest-risk assets will be escalated for AI camera inspection next.
      </div>

      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}>
            <th style={{ padding: "6px 12px 6px 0", textAlign: "left", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Asset</th>
            <th style={{ padding: "6px 12px", textAlign: "left", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Type</th>
            <th style={{ padding: "6px 12px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Score</th>
            {COLUMNS.map((c) => (
              <th key={c.key} style={{ padding: "6px 10px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.asset_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              <td style={{ padding: "5px 12px 5px 0", fontFamily: "monospace", fontSize: 11 }}>{r.asset_id}</td>
              <td style={{ padding: "5px 12px" }}>{r.asset_type}</td>
              <td style={{ padding: "5px 12px", textAlign: "center" }}>
                <span className={badgeClass(r.composite_score)}>{fmt(r.composite_score)}</span>
              </td>
              <td style={{ padding: "5px 10px", textAlign: "center" }}>{fmt(r.breakdown.weather_exposure)}</td>
              <td style={{ padding: "5px 10px", textAlign: "center" }}>{fmt(r.breakdown.age)}</td>
              <td style={{ padding: "5px 10px", textAlign: "center" }}>{fmt(r.breakdown.vegetation)}</td>
              <td style={{ padding: "5px 10px", textAlign: "center" }}>{fmt(r.breakdown.inspection_recency)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.5)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.3 }}>
          Scoring Factors
        </div>
        {COLUMNS.map((c) => (
          <div key={c.key} style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
            <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.75)", minWidth: 40 }}>{c.label}:</span>
            <span style={{ color: "rgba(255,255,255,0.55)" }}>{c.desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
