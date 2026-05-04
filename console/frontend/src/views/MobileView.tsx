// This project was developed with assistance from AI tools.

import { Button } from "@patternfly/react-core";
import type { useEventStream } from "../hooks/useEventStream";

interface MobileViewProps {
  stream: ReturnType<typeof useEventStream>;
}

export function MobileView({ stream }: MobileViewProps) {
  const assignment = stream.dispatches[0];

  return (
    <div style={{ padding: 16, maxWidth: 480, margin: "0 auto", overflowY: "auto", height: "100%" }}>
      <div className="grid-card">
        <div className="grid-card__header">Current Assignment</div>
        <div className="grid-card__body">
          {assignment ? (
            <>
              <div style={{ marginBottom: 8 }}>
                <span className="grid-metric__label">Work Order</span>
                <div style={{ fontWeight: 600 }}>{assignment.work_order_id}</div>
              </div>
              <div style={{ marginBottom: 8 }}>
                <span className="grid-metric__label">Crew</span>
                <div className="grid-mono">{assignment.crew_id}</div>
              </div>
              <div style={{ marginBottom: 8 }}>
                <span className="grid-metric__label">Status</span>
                <div>{assignment.status}</div>
              </div>
            </>
          ) : (
            <div style={{ color: "#6A6E73", textAlign: "center", padding: 16 }}>
              No active assignment
            </div>
          )}
        </div>
      </div>

      <div className="grid-card">
        <div className="grid-card__header">Route &amp; ETA</div>
        <div className="grid-card__body">
          {assignment?.eta_minutes != null ? (
            <div className="grid-metric">
              <div className="grid-metric__label">Estimated Arrival</div>
              <div className="grid-metric__value">{assignment.eta_minutes}m</div>
            </div>
          ) : (
            <div style={{ color: "#6A6E73", textAlign: "center", padding: 16 }}>
              No route available
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, padding: "8px 8px 0" }}>
        <Button variant="primary" isBlock>
          Report Status
        </Button>
        <Button variant="secondary" isBlock>
          Upload Damage Photo
        </Button>
      </div>
    </div>
  );
}
