// This project was developed with assistance from AI tools.

import { useEffect, useMemo, useState } from "react";
import { GridMap } from "../components/GridMap";
import { MapLegend } from "../components/MapLegend";
import { ForecastPipeline } from "../components/ForecastPipeline";
import { TriageOverlay } from "../components/TriageOverlay";
import { DispatchOverlay } from "../components/DispatchOverlay";
import { StormOverlay } from "../components/StormOverlay";
import { SubstationPanel } from "../components/SubstationPanel";
import { RiskTable } from "../components/RiskTable";
import { FindingsPanel } from "../components/FindingsPanel";
import { EventStream } from "../components/EventStream";
import type { TopologyData } from "../types/events";
import type { useEventStream } from "../hooks/useEventStream";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface OperationsViewProps {
  stream: ReturnType<typeof useEventStream>;
  beat: string;
  overlayDismissed: boolean;
  onDismissOverlay: () => void;
}

const KIT_SIGNALING_URL = "kit-substation-grid-ops-ai.apps.v6f8n9h1d3j6g2g.51ty.p1.openshiftapps.com";

const EMPTY_TOPOLOGY: TopologyData = { feeders: [], assets: [], segments: [], cameras: [] };

export function OperationsView({ stream, beat, overlayDismissed, onDismissOverlay }: OperationsViewProps) {
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

  const scenarioActive = stream.events.length > 0;
  const forecastPublished = useMemo(
    () => stream.events.some((e) => e.title?.toLowerCase().includes("corrdiff")),
    [stream.events],
  );

  const showForecast = beat === "forecast" && !overlayDismissed;
  const showTriage = beat === "triage" && !overlayDismissed;
  const showDispatch = beat === "dispatch" && !overlayDismissed;
  const showStorm = beat === "trace" && !overlayDismissed;

  return (
    <div className="grid-layout">
      <div className="grid-layout__left" style={{ position: "relative" }}>
        <MapLegend />
        <ForecastPipeline
          active={showForecast}
          forecastPublished={forecastPublished}
          riskCount={stream.riskScores.size}
          onClose={onDismissOverlay}
        />
        <TriageOverlay
          active={showTriage}
          riskScores={stream.riskScores}
          onClose={onDismissOverlay}
        />
        <DispatchOverlay
          active={showDispatch}
          dispatches={stream.dispatches}
          onClose={onDismissOverlay}
        />
        <StormOverlay
          active={showStorm}
          impact={stream.customerImpact}
          onClose={onDismissOverlay}
        />
        <GridMap
          assets={topology.assets}
          segments={topology.segments}
          cameras={topology.cameras}
          riskScores={stream.riskScores}
          faults={stream.faults}
          dispatches={stream.dispatches}
          scenarioActive={scenarioActive}
        />
      </div>
      <div className="grid-layout__right">
        <SubstationPanel signalingServer={KIT_SIGNALING_URL} />
        <RiskTable riskScores={stream.riskScores} />
        <FindingsPanel findings={stream.findings} />
        <EventStream events={stream.events} />
      </div>
    </div>
  );
}
