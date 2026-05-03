// This project was developed with assistance from AI tools.

import { useEffect, useState } from "react";
import { GridMap } from "../components/GridMap";
import { RiskTable } from "../components/RiskTable";
import { FindingsPanel } from "../components/FindingsPanel";
import { EventStream } from "../components/EventStream";
import type { TopologyData } from "../types/events";
import type { useEventStream } from "../hooks/useEventStream";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface OperationsViewProps {
  stream: ReturnType<typeof useEventStream>;
}

const EMPTY_TOPOLOGY: TopologyData = { feeders: [], assets: [], segments: [], cameras: [] };

export function OperationsView({ stream }: OperationsViewProps) {
  const [topology, setTopology] = useState<TopologyData>(EMPTY_TOPOLOGY);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/topology`);
        if (resp.ok && !cancelled) {
          setTopology(await resp.json());
        }
      } catch {
        /* topology fetch failed — map renders empty */
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="grid-layout">
      <div className="grid-layout__left">
        <GridMap
          assets={topology.assets}
          segments={topology.segments}
          cameras={topology.cameras}
          riskScores={stream.riskScores}
          faults={stream.faults}
          dispatches={stream.dispatches}
        />
      </div>
      <div className="grid-layout__right">
        <RiskTable riskScores={stream.riskScores} />
        <FindingsPanel findings={stream.findings} />
        <EventStream events={stream.events} />
      </div>
    </div>
  );
}
