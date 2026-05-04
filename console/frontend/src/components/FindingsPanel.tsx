// This project was developed with assistance from AI tools.

import { useMemo, useState } from "react";
import type { InspectionFinding, DefectFinding } from "../types/events";

interface FindingsPanelProps {
  findings: InspectionFinding[];
  onSelectAsset?: (assetId: string | null) => void;
}

interface DeduplicatedFinding {
  camera_id: string;
  asset_id: string;
  defect: DefectFinding;
  image_data: string | null;
  timestamp: string;
}

const SEVERITY_CLASS: Record<string, string> = {
  critical: "grid-risk-badge grid-risk-badge--critical",
  major: "grid-risk-badge grid-risk-badge--high",
  warning: "grid-risk-badge grid-risk-badge--medium",
  info: "grid-risk-badge grid-risk-badge--low",
};

const DEFECT_LABELS: Record<string, string> = {
  cracked_crossarm: "Cracked Crossarm",
  vegetation_encroachment: "Vegetation Encroachment",
  ice_accumulation: "Ice Accumulation",
  ice_accumulation_on_conductors: "Ice Accumulation",
  ice_loading: "Ice Loading",
  damaged_insulator: "Damaged Insulator",
  leaning_pole: "Leaning Pole",
  missing_hardware: "Missing Hardware",
  corrosion: "Corrosion",
};

export function FindingsPanel({ findings, onSelectAsset }: FindingsPanelProps) {
  const [selected, setSelected] = useState<DeduplicatedFinding | null>(null);

  const deduplicated = useMemo(() => {
    const latest = new Map<string, DeduplicatedFinding>();
    for (const f of findings) {
      for (const d of f.findings) {
        const key = `${f.camera_id}:${d.defect_type}`;
        if (!latest.has(key)) {
          latest.set(key, {
            camera_id: f.camera_id,
            asset_id: f.asset_id,
            defect: d,
            image_data: f.image_data ?? null,
            timestamp: f.timestamp,
          });
        }
      }
    }
    return Array.from(latest.values());
  }, [findings]);

  const handleSelect = (f: DeduplicatedFinding) => {
    setSelected(f);
    onSelectAsset?.(f.asset_id);
  };

  const handleClose = () => {
    setSelected(null);
    onSelectAsset?.(null);
  };

  return (
    <>
      <div className="grid-card">
        <div className="grid-card__header">Camera Findings</div>
        <div className="grid-card__body--flush" style={{ maxHeight: 220, overflowY: "auto" }}>
          {deduplicated.length === 0 && (
            <div style={{ padding: "12px 16px", color: "#6A6E73", fontSize: 12 }}>
              No findings yet
            </div>
          )}
          {deduplicated.map((f, i) => (
            <div
              key={`${f.camera_id}-${f.defect.defect_type}-${i}`}
              onClick={() => handleSelect(f)}
              style={{
                padding: "8px 16px",
                borderBottom: "1px solid #E0E0E0",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                transition: "background 0.1s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "#f5f5f5"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = ""; }}
            >
              <span className="grid-mono" style={{ fontSize: 11, minWidth: 70 }}>{f.camera_id}</span>
              <span style={{ color: "#6A6E73", fontSize: 10 }}>→</span>
              <span className="grid-mono" style={{ fontSize: 11, minWidth: 40 }}>{f.asset_id}</span>
              <span className={SEVERITY_CLASS[f.defect.severity] ?? SEVERITY_CLASS.info} style={{ fontSize: 10 }}>
                {f.defect.severity}
              </span>
              <span style={{ fontSize: 12, fontWeight: 500, flex: 1 }}>
                {DEFECT_LABELS[f.defect.defect_type] ?? f.defect.defect_type}
              </span>
              <span style={{ fontSize: 10, color: "#6A6E73" }}>
                {(f.defect.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {selected && (
        <div
          onClick={handleClose}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "#fff",
              borderRadius: 8,
              maxWidth: 720,
              width: "90%",
              maxHeight: "85vh",
              overflow: "auto",
              boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
            }}
          >
            <div style={{
              padding: "16px 20px",
              borderBottom: "1px solid #E0E0E0",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="grid-mono" style={{ fontSize: 13 }}>{selected.camera_id}</span>
                <span style={{ color: "#6A6E73" }}>→</span>
                <span className="grid-mono" style={{ fontSize: 13 }}>{selected.asset_id}</span>
                <span className={SEVERITY_CLASS[selected.defect.severity] ?? SEVERITY_CLASS.info}>
                  {selected.defect.severity}
                </span>
              </div>
              <button
                onClick={handleClose}
                style={{
                  border: "none", background: "none", fontSize: 20, cursor: "pointer",
                  color: "#6A6E73", lineHeight: 1,
                }}
              >
                &times;
              </button>
            </div>
            {selected.image_data && (
              <div style={{ padding: 0, background: "#1e1e1e", textAlign: "center" }}>
                <img
                  src={`data:image/png;base64,${selected.image_data}`}
                  alt={`${selected.camera_id} inspection frame`}
                  style={{ maxWidth: "100%", maxHeight: 400, objectFit: "contain" }}
                />
              </div>
            )}
            <div style={{ padding: "16px 20px" }}>
              <h3 style={{ margin: "0 0 8px", fontSize: 16, fontFamily: "Public Sans, sans-serif" }}>
                {DEFECT_LABELS[selected.defect.defect_type] ?? selected.defect.defect_type}
              </h3>
              <div style={{ fontSize: 13, color: "#333", marginBottom: 12, lineHeight: 1.5 }}>
                {selected.defect.description}
              </div>
              <div style={{ fontSize: 12, color: "#6A6E73" }}>
                <div><strong>Confidence:</strong> {(selected.defect.confidence * 100).toFixed(0)}%</div>
                {selected.defect.recommended_action && (
                  <div style={{ marginTop: 4 }}><strong>Recommended Action:</strong> {selected.defect.recommended_action}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
