// This project was developed with assistance from AI tools.

interface SubstationPanelProps {
  signalingServer: string;
}

export function SubstationPanel({ signalingServer }: SubstationPanelProps) {
  return (
    <div className="grid-card" style={{ height: 300, display: "flex", flexDirection: "column" }}>
      <div className="grid-card__header">3D Substation Digital Twin</div>
      <div
        className="grid-card__body"
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#1e1e1e",
          color: "#ccc",
          fontSize: 13,
          gap: 8,
        }}
      >
        <span>Connecting to substation digital twin...</span>
        <span className="grid-mono" style={{ fontSize: 11 }}>
          WebRTC: {signalingServer}
        </span>
        <span style={{ fontSize: 11, color: "#888", marginTop: 4 }}>
          Requires @nvidia/omniverse-webrtc-streaming-library
        </span>
      </div>
    </div>
  );
}
