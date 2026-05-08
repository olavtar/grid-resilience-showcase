// This project was developed with assistance from AI tools.

const CARDS = [
  {
    title: "Autonomous Drone Fleet Inspection",
    description: "AI-powered drone fleets autonomously inspect thousands of poles and substations. Computer vision models trained on synthetic data generated in Omniverse detect defects in minutes — reducing inspection time from hours to seconds per asset.",
    products: ["Jetson", "Omniverse"],
    metric: "100x faster inspections",
    detail: "Utilities have deployed autonomous drone-and-dock systems that fly preprogrammed routes, capture high-resolution and thermal imagery, and deliver AI-analyzed results in under 5 minutes per flight.",
    deployedBy: "Exelon, Deloitte",
  },
  {
    title: "Grid-Edge AI at Scale",
    description: "AI-powered smart meters and edge devices deployed at substations and on poles run inference locally — detecting faults, monitoring power quality, and managing distributed energy resources in real time without cloud latency.",
    products: ["Jetson Orin"],
    metric: "Scaling to 100,000+ edge devices",
    detail: "Edge AI modules embedded in smart meters process grid telemetry at the device level. Only alerts and aggregated insights travel to the operations center, keeping latency under 2 seconds. DOE-funded deployments are scaling to six figures.",
    deployedBy: "Utilidata, Consumers Energy, Portland General Electric",
  },
  {
    title: "GPU-Accelerated Grid Planning",
    description: "Interconnection studies that previously took 30-45 days per request now complete in minutes. GPU-accelerated power flow analysis runs millions of scenarios simultaneously, clearing the backlog of renewable energy projects waiting to connect.",
    products: ["CUDA", "cuDSS"],
    metric: "Month-long studies in 3 minutes",
    detail: "Physics-informed AI digital twins of distribution networks run 10 million power flow scenarios in 10 minutes with over 99.7% accuracy — transforming grid planning from a bottleneck into a competitive advantage.",
    deployedBy: "ThinkLabs AI, Southern California Edison",
  },
  {
    title: "Physics-Informed Asset Digital Twins",
    description: "High-fidelity digital twins of critical grid assets — transformers, switchgear, generators — simulate thermal behavior and predict failures before they occur, using AI surrogate models trained on physics simulations.",
    products: ["PhysicsNeMo", "Omniverse"],
    metric: "10,000x simulation speedup",
    detail: "AI surrogate models predict transformer hotspot temperatures under varying load conditions with less than 4% error, enabling predictive maintenance that could prevent billions in unplanned downtime annually.",
    deployedBy: "Siemens Energy",
  },
  {
    title: "AI-Powered Renewable Forecasting",
    description: "Earth-2 weather models provide hyperlocal wind and solar irradiance predictions that improve renewable energy dispatch. Grid operators use GPU-accelerated ensemble forecasting to run thousands of scenarios in seconds.",
    products: ["Earth-2", "FourCastNet", "CorrDiff"],
    metric: "Adopted by grid operators",
    detail: "Regional grid operators use Earth-2 models for intraday and day-ahead wind forecasting across multi-state footprints, improving reliability and reducing curtailment of renewable generation.",
    deployedBy: "Southwest Power Pool, GCL",
  },
  {
    title: "Real-Time Substation Video Analytics",
    description: "AI vision pipelines monitor live substation camera feeds for security intrusions, safety incidents, equipment anomalies, and fire or arcing detection — turning existing security cameras into intelligent monitoring systems.",
    products: ["Metropolis", "DeepStream", "Jetson"],
    metric: "24/7 autonomous monitoring",
    detail: "Container-based vision AI deployed on-premises at substations processes streaming video in real time, replacing periodic human review with continuous AI surveillance that never blinks.",
    deployedBy: "Buzz Solutions, Southern California Edison, NYPA",
  },
];

export function WhatsNextView() {
  return (
    <div style={{ padding: 32, overflowY: "auto", height: "100%", background: "#f5f5f5" }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 26, fontWeight: 700, fontFamily: "Public Sans, sans-serif", margin: 0, color: "#151515" }}>
            From Demo to Production
          </h2>
          <p style={{ fontSize: 16, color: "#6A6E73", marginTop: 8, maxWidth: 800, lineHeight: 1.6 }}>
            What you've seen today is a functional slice of a larger AI-powered grid operations platform.
            Here's where utilities are taking this technology at production scale.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}>
          {CARDS.map((card) => (
            <div
              key={card.title}
              style={{
                background: "#fff",
                border: "1px solid #E0E0E0",
                borderRadius: 8,
                padding: 28,
                display: "flex",
                flexDirection: "column",
                gap: 14,
              }}
            >
              <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "Public Sans, sans-serif", color: "#151515" }}>
                {card.title}
              </div>
              <div style={{ fontSize: 15, color: "#4a4a4a", lineHeight: 1.6 }}>
                {card.description}
              </div>
              <div style={{
                display: "inline-flex",
                alignSelf: "flex-start",
                background: "#151515",
                color: "#fff",
                fontSize: 15,
                fontWeight: 600,
                padding: "6px 16px",
                borderRadius: 4,
                fontFamily: "Public Sans, sans-serif",
              }}>
                {card.metric}
              </div>
              <div style={{ fontSize: 14, color: "#6A6E73", lineHeight: 1.6, fontStyle: "italic" }}>
                {card.detail}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: "auto", paddingTop: 10 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {card.products.map((p) => (
                    <span
                      key={p}
                      style={{
                        fontSize: 12,
                        padding: "3px 10px",
                        borderRadius: 3,
                        background: "rgba(21,21,21,0.06)",
                        color: "#151515",
                        fontWeight: 500,
                      }}
                    >
                      {p}
                    </span>
                  ))}
                </div>
                {card.deployedBy && (
                  <span style={{ fontSize: 10, color: "#999", fontStyle: "italic", whiteSpace: "nowrap", marginLeft: 12 }}>
                    {card.deployedBy}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
