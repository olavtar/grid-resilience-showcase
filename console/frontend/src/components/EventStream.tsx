// This project was developed with assistance from AI tools.

import type { OpsEvent } from "../types/events";

interface EventStreamProps {
  events: OpsEvent[];
}

const CATEGORY_CLASS: Record<string, string> = {
  weather: "grid-dot--weather",
  risk: "grid-dot--risk",
  camera: "grid-dot--camera",
  dispatch: "grid-dot--dispatch",
  fault: "grid-dot--fault",
  restoration: "grid-dot--restoration",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function EventStream({ events }: EventStreamProps) {
  return (
    <div className="grid-card">
      <div className="grid-card__header">Event Stream</div>
      <div className="grid-card__body--flush" style={{ maxHeight: 220, overflowY: "auto" }}>
        {events.length === 0 && (
          <div style={{ padding: "12px 16px", color: "#6A6E73", fontSize: 12 }}>
            Waiting for events...
          </div>
        )}
        {events.map((e) => (
          <div key={e.event_id} className="grid-event-row">
            <span className={`grid-dot ${CATEGORY_CLASS[e.category] ?? "grid-dot--system"}`} />
            <span className="grid-event-row__time">{formatTime(e.timestamp)}</span>
            <span className="grid-event-row__title">{e.title}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
