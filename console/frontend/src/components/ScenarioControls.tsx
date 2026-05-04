// This project was developed with assistance from AI tools.

import { useCallback, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface ScenarioControlsProps {
  onReset?: () => void;
}

const BEATS = [
  { id: "forecast", label: "Forecast" },
  { id: "triage", label: "Triage" },
  { id: "escalate", label: "Escalate" },
  { id: "detect", label: "Detect" },
  { id: "dispatch", label: "Dispatch" },
  { id: "storm", label: "Storm" },
  { id: "trace", label: "Trace" },
];

export function ScenarioControls({ onReset }: ScenarioControlsProps) {
  const [beat, setBeat] = useState("idle");

  const post = useCallback(async (action: string) => {
    try {
      const resp = await fetch(`${API_BASE}/api/scenario/${action}`, { method: "POST" });
      if (resp.ok) {
        const data = await resp.json();
        setBeat(data.beat ?? data.current_beat ?? "idle");
        if (action === "reset") onReset?.();
      }
    } catch {
      /* connection error handled by SSE reconnect */
    }
  }, [onReset]);

  const beatIndex = BEATS.findIndex((b) => b.id === beat);

  return (
    <div className="grid-controls">
      <button className="grid-controls__button grid-controls__button--primary" onClick={() => post("start")}>
        Start
      </button>
      <button className="grid-controls__button" onClick={() => post("advance")}>
        Advance
      </button>
      <button className="grid-controls__button" onClick={() => post("trigger-storm")}>
        Storm
      </button>
      <button className="grid-controls__button" onClick={() => post("trigger-fault")}>
        Fault
      </button>
      <button className="grid-controls__button" onClick={() => post("reset")}>
        Reset
      </button>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 2 }}>
        {BEATS.map((b, i) => {
          const isActive = b.id === beat;
          const isPast = beatIndex >= 0 && i < beatIndex;
          return (
            <div key={b.id} style={{ display: "flex", alignItems: "center", gap: 2 }}>
              <span
                style={{
                  fontSize: 11,
                  fontFamily: "Inter, sans-serif",
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? "#3E8635" : isPast ? "rgba(62,134,53,0.7)" : "rgba(255,255,255,0.35)",
                  transition: "all 0.2s ease",
                  padding: "2px 4px",
                  borderRadius: 3,
                  background: isActive ? "rgba(62,134,53,0.15)" : "transparent",
                }}
              >
                {b.label}
              </span>
              {i < BEATS.length - 1 && (
                <span style={{
                  fontSize: 10,
                  color: isPast ? "rgba(62,134,53,0.5)" : "rgba(255,255,255,0.2)",
                }}>›</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
