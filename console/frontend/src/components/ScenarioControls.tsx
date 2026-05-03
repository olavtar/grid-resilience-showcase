// This project was developed with assistance from AI tools.

import { useCallback, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function ScenarioControls() {
  const [beat, setBeat] = useState("idle");
  const [solveTime] = useState<string | null>(null);

  const post = useCallback(async (action: string) => {
    try {
      const resp = await fetch(`${API_BASE}/api/scenario/${action}`, { method: "POST" });
      if (resp.ok) {
        const data = await resp.json();
        setBeat(data.beat ?? data.current_beat ?? beat);
      }
    } catch {
      /* connection error handled by SSE reconnect */
    }
  }, [beat]);

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
      <span className="grid-controls__status">
        Beat: {beat}
        {solveTime && ` | cuOpt: ${solveTime}`}
      </span>
    </div>
  );
}
