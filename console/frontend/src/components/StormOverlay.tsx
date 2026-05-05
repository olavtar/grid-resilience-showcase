// This project was developed with assistance from AI tools.

import type { CustomerImpact } from "../types/events";

interface StormOverlayProps {
  active: boolean;
  impact: CustomerImpact | null;
  onClose: () => void;
}

export function StormOverlay({ active, impact, onClose }: StormOverlayProps) {
  if (!active) return null;

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
        <span style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, color: "#A30000" }}>
          Storm Response
        </span>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "rgba(255,255,255,0.4)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 0 }}
        >
          ×
        </button>
      </div>

      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", marginBottom: 14, lineHeight: 1.5, maxWidth: 520, whiteSpace: "normal" }}>
        The ice storm predicted by CorrDiff has arrived. Crews dispatched by cuOpt are already en route to priority assets. Automatic switching has restored partial service.
      </div>

      <div style={{ display: "flex", gap: 24, marginBottom: 14 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#A30000" }}>{impact?.total_affected ?? "847"}</div>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Affected</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#3E8635" }}>{impact?.restored ?? "312"}</div>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Restored</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#F0AB00" }}>{impact?.remaining ?? "535"}</div>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Remaining</div>
        </div>
        {(impact?.etr_minutes ?? 135) > 0 && (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: "rgba(255,255,255,0.8)" }}>{Math.floor((impact?.etr_minutes ?? 135) / 60)}h {(impact?.etr_minutes ?? 135) % 60}m</div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Est. Restore</div>
          </div>
        )}
      </div>

      <div style={{ marginTop: 4, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.5)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.3 }}>
          Response Timeline
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ color: "#3E8635" }}>✓</span>
          <span style={{ color: "rgba(255,255,255,0.75)" }}>Fault detected on Feeder F-12 via AMI smart meters</span>
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ color: "#3E8635" }}>✓</span>
          <span style={{ color: "rgba(255,255,255,0.75)" }}>Automatic tie-switch closure restored 312 customers</span>
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ color: "#3E8635" }}>✓</span>
          <span style={{ color: "rgba(255,255,255,0.75)" }}>Crews already dispatched — en route before fault occurred</span>
        </div>
        <div style={{ display: "flex", gap: 10, padding: "4px 0", fontSize: 12 }}>
          <span style={{ color: "#F0AB00" }}>◉</span>
          <span style={{ color: "rgba(255,255,255,0.75)" }}>Repair crews working to restore remaining customers</span>
        </div>
      </div>
    </div>
  );
}
