// This project was developed with assistance from AI tools.

import { useMemo } from "react";
import type { OpsEvent } from "../types/events";

interface EventStreamProps {
  events: OpsEvent[];
}

interface GroupedEvent {
  event: OpsEvent;
  count: number;
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
  const grouped = useMemo(() => {
    const seen = new Map<string, GroupedEvent>();
    const order: string[] = [];
    for (const e of events) {
      const key = `${e.category}:${e.title}`;
      const existing = seen.get(key);
      if (existing) {
        existing.count++;
      } else {
        const g = { event: e, count: 1 };
        seen.set(key, g);
        order.push(key);
      }
    }
    return order.map((k) => seen.get(k)!);
  }, [events]);

  return (
    <div className="grid-card">
      <div className="grid-card__header">Event Stream</div>
      <div className="grid-card__body--flush" style={{ maxHeight: 220, overflowY: "auto" }}>
        {grouped.length === 0 && (
          <div style={{ padding: "12px 16px", color: "#6A6E73", fontSize: 12 }}>
            Waiting for events...
          </div>
        )}
        {grouped.map((g) => (
          <div key={g.event.event_id} className="grid-event-row">
            <span className={`grid-dot ${CATEGORY_CLASS[g.event.category] ?? "grid-dot--system"}`} />
            <span className="grid-event-row__time">{formatTime(g.event.timestamp)}</span>
            <span className="grid-event-row__title">{g.event.title}</span>
            {g.count > 1 && (
              <span style={{
                fontSize: 10, fontWeight: 600, color: "#fff",
                background: "#6A6E73", borderRadius: 8,
                padding: "1px 6px", marginLeft: 4,
              }}>
                {g.count}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
