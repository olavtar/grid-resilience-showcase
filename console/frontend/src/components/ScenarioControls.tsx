// This project was developed with assistance from AI tools.

import { useCallback, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface ScenarioControlsProps {
  onReset?: () => void;
}

const BEATS = ["forecast", "triage", "escalate", "detect", "dispatch", "storm", "trace"];

export function ScenarioControls({ onReset }: ScenarioControlsProps) {
  const [beat, setBeat] = useState("idle");
  const [solveTime] = useState<string | null>(null);

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

  const beatIndex = BEATS.indexOf(beat);

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
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
        {BEATS.map((b, i) => {
          const isActive = b === beat;
          const isPast = beatIndex >= 0 && i < beatIndex;
          return (
            <div key={b} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: isActive ? "#3E8635" : isPast ? "rgba(62,134,53,0.5)" : "rgba(255,255,255,0.25)",
                  border: isActive ? "2px solid #fff" : "none",
                  transition: "all 0.2s ease",
                }}
                title={b}
              />
              {i < BEATS.length - 1 && (
                <div style={{
                  width: 12,
                  height: 2,
                  background: isPast ? "rgba(62,134,53,0.5)" : "rgba(255,255,255,0.15)",
                }} />
              )}
            </div>
          );
        })}
        <span style={{ marginLeft: 8, fontSize: 11, color: "rgba(255,255,255,0.6)", fontFamily: "monospace" }}>
          {beat === "idle" ? "ready" : beat}
          {solveTime && ` | cuOpt: ${solveTime}`}
        </span>
      </div>
    </div>
  );
}
