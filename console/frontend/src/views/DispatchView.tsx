// This project was developed with assistance from AI tools.

import { useCallback, useState } from "react";
import { Button } from "@patternfly/react-core";
import type { useEventStream } from "../hooks/useEventStream";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface DispatchViewProps {
  stream: ReturnType<typeof useEventStream>;
}

export function DispatchView({ stream }: DispatchViewProps) {
  const [justifications, setJustifications] = useState<Record<string, string>>({});
  const [actionedPlans, setActionedPlans] = useState<Set<string>>(new Set());

  const approve = useCallback(async (planId: string, action: "approve" | "reject") => {
    try {
      await fetch(`${API_BASE}/api/dispatch/${action}/${planId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ justification: justifications[planId] ?? "" }),
      });
      setActionedPlans((prev) => new Set(prev).add(planId));
    } catch {
      /* connection error handled by SSE reconnect */
    }
  }, [justifications]);

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      <div className="grid-card">
        <div className="grid-card__header">Dispatcher Review</div>
        <div className="grid-card__body--flush">
          <table className="grid-risk-table">
            <thead>
              <tr>
                <th>Crew</th>
                <th>Work Order</th>
                <th>Status</th>
                <th>ETA</th>
                <th>Guardrails</th>
                <th>Justification</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stream.dispatches.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ color: "#6A6E73", textAlign: "center", padding: 12 }}>
                    No dispatch assignments
                  </td>
                </tr>
              )}
              {stream.dispatches.map((d) => {
                const actioned = actionedPlans.has(d.plan_id);
                return (
                  <tr key={d.plan_id}>
                    <td className="grid-mono">{d.crew_id}</td>
                    <td className="grid-mono">{d.work_order_id}</td>
                    <td>{d.status}</td>
                    <td>{d.eta_minutes != null ? `${d.eta_minutes}m` : "—"}</td>
                    <td>
                      {d.guardrails_result === "pass" ? (
                        <span style={{ color: "#3E8635", fontWeight: 500 }}>Pass</span>
                      ) : d.guardrails_result === "fail" ? (
                        <span style={{ color: "#A30000", fontWeight: 500 }}>Fail</span>
                      ) : (
                        <span style={{ color: "#6A6E73" }}>—</span>
                      )}
                    </td>
                    <td>
                      <input
                        type="text"
                        placeholder="Justification..."
                        value={justifications[d.plan_id] ?? ""}
                        onChange={(e) =>
                          setJustifications((prev) => ({ ...prev, [d.plan_id]: e.target.value }))
                        }
                        disabled={actioned}
                        style={{
                          width: "100%",
                          padding: "2px 6px",
                          fontSize: 12,
                          border: "1px solid #E0E0E0",
                          borderRadius: 3,
                        }}
                      />
                    </td>
                    <td style={{ display: "flex", gap: 4 }}>
                      <Button
                        variant="primary"
                        size="sm"
                        isDisabled={actioned}
                        onClick={() => approve(d.plan_id, "approve")}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        isDisabled={actioned}
                        onClick={() => approve(d.plan_id, "reject")}
                      >
                        Reject
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
