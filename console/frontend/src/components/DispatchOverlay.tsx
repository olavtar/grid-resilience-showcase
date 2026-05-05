// This project was developed with assistance from AI tools.

import type { DispatchAssignment } from "../types/events";

interface DispatchOverlayProps {
  active: boolean;
  dispatches: DispatchAssignment[];
  onClose: () => void;
}

function statusLabel(s: string): string {
  if (s === "pending_approval") return "Pending";
  if (s === "approved") return "Approved";
  return s;
}

const GUARD_ORDER: Record<string, number> = { pass: 0, warn: 1, block: 2 };

export function DispatchOverlay({ active, dispatches, onClose }: DispatchOverlayProps) {
  if (!active) return null;

  const sorted = [...dispatches].sort(
    (a, b) => (GUARD_ORDER[a.guardrails_result ?? "pass"] ?? 0) - (GUARD_ORDER[b.guardrails_result ?? "pass"] ?? 0),
  );

  const solveTime = dispatches[0]?.cuopt_solve_time_ms;

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
      whiteSpace: "nowrap" as const,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "rgba(255,255,255,0.6)" }}>
          cuOpt Crew Dispatch
        </span>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 0 }}
        >
          ×
        </button>
      </div>

      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", marginBottom: 14, lineHeight: 1.5, maxWidth: 580, whiteSpace: "normal" }}>
        NVIDIA cuOpt solves a vehicle routing problem across available crews — optimizing for travel distance, crew skills, shift availability, and work order priority.
        {solveTime != null && (
          <span style={{ color: "rgba(255,255,255,0.5)" }}> Solved in {(solveTime / 1000).toFixed(1)}s on GPU.</span>
        )}
      </div>

      {sorted.length > 0 ? (
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}>
              <th style={{ padding: "6px 12px 6px 0", textAlign: "left", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Crew</th>
              <th style={{ padding: "6px 12px", textAlign: "left", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Assignment</th>
              <th style={{ padding: "6px 12px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>ETA</th>
              <th style={{ padding: "6px 12px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Status</th>
              <th style={{ padding: "6px 12px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontWeight: 500 }}>Safety</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((d, i) => {
              const blocked = d.guardrails_result === "block";
              return (
                <tr key={`${d.crew_id}-${i}`} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", opacity: blocked ? 0.5 : 1 }}>
                  <td style={{ padding: "5px 12px 5px 0", fontFamily: "monospace", fontSize: 11 }}>{d.crew_id}</td>
                  <td style={{ padding: "5px 12px" }}>{d.work_order_title ?? d.work_order_id.slice(0, 8)}</td>
                  <td style={{ padding: "5px 12px", textAlign: "center" }}>{d.eta_minutes != null ? `${Math.round(d.eta_minutes)}m` : "—"}</td>
                  <td style={{ padding: "5px 12px", textAlign: "center" }}>{statusLabel(d.status)}</td>
                  <td style={{ padding: "5px 12px", textAlign: "center" }}>
                    {d.guardrails_result === "pass" ? (
                      <span style={{ color: "#3E8635" }}>Pass</span>
                    ) : blocked ? (
                      <span style={{ color: "#A30000" }}>Block</span>
                    ) : (
                      <span style={{ color: "#6A6E73" }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", padding: "8px 0" }}>
          Waiting for cuOpt optimization...
        </div>
      )}

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.5)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.3 }}>
          Optimization Factors
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.75)" }}>Distance:</span>
          <span style={{ color: "rgba(255,255,255,0.55)" }}>Minimizes total crew travel across all assignments</span>
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.75)" }}>Skills:</span>
          <span style={{ color: "rgba(255,255,255,0.55)" }}>Matches crew certifications to work order requirements</span>
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.75)" }}>Priority:</span>
          <span style={{ color: "rgba(255,255,255,0.55)" }}>Critical work orders weighted higher for assignment</span>
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: "rgba(255,255,255,0.75)" }}>Safety:</span>
          <span style={{ color: "rgba(255,255,255,0.55)" }}>NeMo Guardrails validates each assignment post-optimization</span>
        </div>
      </div>
    </div>
  );
}
