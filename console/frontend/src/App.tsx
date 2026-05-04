// This project was developed with assistance from AI tools.

import { useState } from "react";
import { Masthead } from "./components/Masthead";
import { ScenarioControls } from "./components/ScenarioControls";
import { CustomerImpactBanner } from "./components/CustomerImpactBanner";
import { OperationsView } from "./views/OperationsView";
import { DispatchView } from "./views/DispatchView";
import { PlatformView } from "./views/PlatformView";
import { MobileView } from "./views/MobileView";
import { useEventStream } from "./hooks/useEventStream";
import "@patternfly/react-core/dist/styles/base.css";
import "./styles/grid-ops.css";

type ViewId = "operations" | "dispatch" | "platform" | "mobile";

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("operations");
  const stream = useEventStream();

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Masthead activeView={activeView} onViewChange={(v) => setActiveView(v as ViewId)} connected={stream.connected} />
      <CustomerImpactBanner impact={stream.customerImpact} />
      <div style={{ flex: 1, overflow: "hidden" }}>
        {activeView === "operations" && <OperationsView stream={stream} />}
        {activeView === "dispatch" && <DispatchView stream={stream} />}
        {activeView === "platform" && <PlatformView />}
        {activeView === "mobile" && <MobileView stream={stream} />}
      </div>
      <ScenarioControls onReset={stream.reset} />
    </div>
  );
}
