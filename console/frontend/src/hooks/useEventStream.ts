// This project was developed with assistance from AI tools.

import { useCallback, useEffect, useRef, useState } from "react";
import type { OpsEvent, AssetRiskScore, FaultEvent, CustomerImpact, DispatchAssignment, InspectionFinding } from "../types/events";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface GridState {
  events: OpsEvent[];
  riskScores: Map<string, AssetRiskScore>;
  findings: InspectionFinding[];
  dispatches: DispatchAssignment[];
  faults: FaultEvent[];
  customerImpact: CustomerImpact | null;
  connected: boolean;
}

export function useEventStream(): GridState {
  const [events, setEvents] = useState<OpsEvent[]>([]);
  const [riskScores, setRiskScores] = useState<Map<string, AssetRiskScore>>(new Map());
  const [findings, setFindings] = useState<InspectionFinding[]>([]);
  const [dispatches, setDispatches] = useState<DispatchAssignment[]>([]);
  const [faults, setFaults] = useState<FaultEvent[]>([]);
  const [customerImpact, setCustomerImpact] = useState<CustomerImpact | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    const es = new EventSource(`${API_BASE}/api/events`);
    esRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => {
      setConnected(false);
      es.close();
      setTimeout(connect, 3000);
    };

    es.addEventListener("grid.ops.events", (e) => {
      const data = JSON.parse(e.data) as OpsEvent;
      setEvents((prev) => [data, ...prev].slice(0, 200));
    });

    es.addEventListener("grid.assets.risk-scores", (e) => {
      const data = JSON.parse(e.data) as AssetRiskScore;
      setRiskScores((prev) => new Map(prev).set(data.asset_id, data));
    });

    es.addEventListener("grid.cameras.findings", (e) => {
      const data = JSON.parse(e.data) as InspectionFinding;
      setFindings((prev) => [data, ...prev].slice(0, 100));
    });

    es.addEventListener("grid.crew.dispatch", (e) => {
      const data = JSON.parse(e.data) as DispatchAssignment;
      setDispatches((prev) => [data, ...prev].slice(0, 50));
    });

    es.addEventListener("grid.faults.detected", (e) => {
      const data = JSON.parse(e.data) as FaultEvent;
      setFaults((prev) => [data, ...prev]);
    });

    es.addEventListener("grid.customer.impact", (e) => {
      const data = JSON.parse(e.data) as CustomerImpact;
      setCustomerImpact(data);
    });
  }, []);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
    };
  }, [connect]);

  return { events, riskScores, findings, dispatches, faults, customerImpact, connected };
}
