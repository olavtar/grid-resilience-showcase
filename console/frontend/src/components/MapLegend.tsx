// This project was developed with assistance from AI tools.

const ITEMS = [
  { color: "#3E8635", label: "Low risk" },
  { color: "#F0AB00", label: "Medium risk" },
  { color: "#EE0000", label: "High risk" },
  { color: "#A30000", label: "Critical risk" },
  { color: "#0066CC", shape: "diamond" as const, label: "Camera" },
  { color: "#A30000", shape: "ring" as const, label: "Fault" },
  { color: "rgba(0,102,204,0.15)", shape: "rect" as const, label: "Storm coverage" },
];

export function MapLegend() {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 32,
        left: 12,
        background: "rgba(255,255,255,0.92)",
        border: "1px solid #E0E0E0",
        borderRadius: 4,
        padding: "8px 12px",
        fontSize: 11,
        fontFamily: "Inter, sans-serif",
        zIndex: 10,
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      {ITEMS.map((item) => (
        <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {item.shape === "diamond" ? (
            <div style={{
              width: 8, height: 8, background: item.color,
              transform: "rotate(45deg)", flexShrink: 0,
            }} />
          ) : item.shape === "ring" ? (
            <div style={{
              width: 10, height: 10, borderRadius: "50%",
              border: `2px solid ${item.color}`, opacity: 0.7, flexShrink: 0,
            }} />
          ) : item.shape === "rect" ? (
            <div style={{
              width: 12, height: 8, background: item.color,
              border: "1px solid rgba(0,102,204,0.3)", flexShrink: 0,
            }} />
          ) : (
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: item.color, flexShrink: 0,
            }} />
          )}
          <span style={{ color: "#151515" }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
