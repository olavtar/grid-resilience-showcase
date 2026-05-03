// This project was developed with assistance from AI tools.

import type { InspectionFinding } from "../types/events";

interface FindingsPanelProps {
  findings: InspectionFinding[];
}

const SEVERITY_CLASS: Record<string, string> = {
  critical: "grid-risk-badge grid-risk-badge--critical",
  major: "grid-risk-badge grid-risk-badge--high",
  warning: "grid-risk-badge grid-risk-badge--medium",
  info: "grid-risk-badge grid-risk-badge--low",
};

export function FindingsPanel({ findings }: FindingsPanelProps) {
  return (
    <div className="grid-card">
      <div className="grid-card__header">Camera Findings</div>
      <div className="grid-card__body--flush" style={{ maxHeight: 260, overflowY: "auto" }}>
        {findings.length === 0 && (
          <div style={{ padding: "12px 16px", color: "#6A6E73", fontSize: 12 }}>
            No findings yet
          </div>
        )}
        {findings.map((f) =>
          f.findings.map((d, i) => (
            <div key={`${f.event_id}-${i}`} style={{ padding: "10px 16px", borderBottom: "1px solid #E0E0E0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span className="grid-mono">{f.camera_id}</span>
                <span style={{ color: "#6A6E73", fontSize: 11 }}>→</span>
                <span className="grid-mono">{f.asset_id}</span>
                <span className={SEVERITY_CLASS[d.severity] ?? SEVERITY_CLASS.info}>{d.severity}</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{d.defect_type}</div>
              <div style={{ fontSize: 12, color: "#6A6E73" }}>{d.description}</div>
              <div style={{ fontSize: 11, color: "#6A6E73", marginTop: 4 }}>
                Confidence: {(d.confidence * 100).toFixed(0)}%
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
