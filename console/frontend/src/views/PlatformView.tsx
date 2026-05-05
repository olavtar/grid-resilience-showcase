// This project was developed with assistance from AI tools.

export function PlatformView() {
  return (
    <div style={{
      height: "100%",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "#f5f5f5",
      padding: 24,
    }}>
      <img
        src="/platform-wip.png"
        alt="Platform view coming soon"
        style={{ maxWidth: "100%", maxHeight: "70vh", borderRadius: 8, boxShadow: "0 4px 20px rgba(0,0,0,0.15)" }}
      />
      <p style={{ marginTop: 16, fontSize: 14, color: "#6A6E73", fontFamily: "Inter, sans-serif" }}>
        OpenShift platform status, Argo CD sync, and GPU utilization — coming soon.
      </p>
    </div>
  );
}
