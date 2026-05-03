// This project was developed with assistance from AI tools.

export function PlatformView() {
  return (
    <div style={{ padding: 16, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, height: "100%" }}>
      <div className="grid-card">
        <div className="grid-card__header">OpenShift Topology</div>
        <div className="grid-card__body">
          <div className="grid-metric">
            <div className="grid-metric__label">Cluster Status</div>
            <div className="grid-metric__value" style={{ color: "#3E8635" }}>Healthy</div>
          </div>
          <p style={{ padding: "12px 0", color: "#6A6E73", fontSize: 12 }}>
            Topology visualization will show running pods, services, and routes across the grid-ops namespace.
          </p>
        </div>
      </div>

      <div className="grid-card">
        <div className="grid-card__header">Argo CD Status</div>
        <div className="grid-card__body">
          <div className="grid-metric">
            <div className="grid-metric__label">Sync State</div>
            <div className="grid-metric__value" style={{ color: "#3E8635" }}>Synced</div>
          </div>
          <p style={{ padding: "12px 0", color: "#6A6E73", fontSize: 12 }}>
            GitOps reconciliation status for all ApplicationSets managed by this repository.
          </p>
        </div>
      </div>

      <div className="grid-card">
        <div className="grid-card__header">GPU Utilization</div>
        <div className="grid-card__body">
          <div className="grid-metric">
            <div className="grid-metric__label">Allocated GPUs</div>
            <div className="grid-metric__value">3 / 3</div>
          </div>
          <div style={{ padding: "8px 0", fontSize: 12, color: "#6A6E73" }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
              <span>L40S #1 — CorrDiff NIM</span>
              <span className="grid-mono">~40 GB</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
              <span>L40S #2 — Cosmos Reason (vLLM)</span>
              <span className="grid-mono">~32 GB</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
              <span>L4 — Omniverse Kit</span>
              <span className="grid-mono">~16 GB</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
