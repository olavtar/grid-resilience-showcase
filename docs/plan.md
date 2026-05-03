# Grid Resilience Operations Center — Implementation Plan

## Context

Red Hat leadership asked for an energy-vertical demo targeting utility companies (Duke Energy, SCE, Exelon, Endeavor, etc.). After researching NVIDIA's energy stack (Earth-2, cuOpt, PhysicsNeMo, Metropolis) and what utilities actually spend money on (predictive maintenance, vegetation management, weather-driven operations, crew dispatch), we designed a demo concept: **Grid Resilience Operations Center**.

This is a **standalone project** — not an extension of the warehouse showcase. The warehouse demo's visual anchor is Isaac Sim (3D robot world). This demo's anchor is a **map-based AI operations console** powered by real NVIDIA inference (Earth-2 weather, cuOpt optimization, Cosmos Reason perception). Different center of gravity, different products, different story.

**Geographic setting**: Piedmont North Carolina (Duke Energy territory). Ice storms are the primary threat. Duke is an NVIDIA OPAI consortium founding member with an $83B capital plan and heavy AI investment. The scenario YAML is geography-pluggable — future packs for Gulf Coast hurricanes, California wildfire/PSPS, and Midwest derecho are planned as stretch goals using the same service architecture with different seed data, weather events, and imagery sets.

---

## 1. Demo Narrative — Beat-by-Beat Script

### Hallway Hook Variant (90 seconds — conference booth / hallway)

Start at Beat 6. The storm is already raging. A fault fires. cuOpt re-optimizes all crew routes in 200ms. The customer impact counter ticks — "2,340 customers affected, ETR updating." Crews reroute on the map. Then rewind: "Let me show you how we got here — 18 hours before the storm, the system already knew this was coming." Transition to Beat 1 of the full demo. This inverts the narrative from chronological to dramatic — lead with the payoff, earn the right to explain the setup.

### Full Demo (5 minutes — boardroom / scheduled meeting)

### Beat 1: Forecast (0:00–0:45)

**What the customer sees**: The console opens with a split layout — a map of the Piedmont NC distribution corridor on the left (~15 miles of feeders, 80+ poles, 2 substations), and a 3D substation digital twin on the right, rendered by NVIDIA Omniverse. All equipment in the 3D scene is green/normal. The narrator: "This is one of your substations — rendered as a real-time digital twin by NVIDIA Omniverse, running on OpenShift."

Earth-2 weather overlay fades into the map — wind vectors, temperature gradient, precipitation type forecast. A timeline slider shows the storm approaching over the next 18 hours. Ice accumulation forecast intensifies over the northern section of the corridor. The risk heat map activates — asset markers on the map shift from green → yellow → orange → red as their risk scores climb.

**Narrator note (Red Hat platform visibility)**: "This Earth-2 weather model is deployed as an NVIDIA NIM container, managed by the GPU Operator on Red Hat OpenShift. OpenShift handles driver lifecycle, GPU scheduling, and health monitoring — your operations team doesn't touch CUDA drivers."

**What's happening technically**: The Weather Service has run Earth-2 (CorrDiff NIM) to produce a 3km downscaled forecast for the Piedmont region. Output variables: 2m temperature (t2m), 10m wind components (u10m/v10m), precipitation type (crain/cfrzr/cicep/csnow), total precipitation (tp). The Risk Engine consumes this forecast, queries the asset database for every asset in the affected corridor, and computes per-asset risk scores combining weather exposure, asset age, vegetation proximity, and inspection history. Scores are published to Kafka and the console renders them on the map. The Kit substation scene receives risk score updates via Kafka but no substation equipment has crossed the threshold yet — the 3D scene remains green.

**NVIDIA products**: Earth-2 CorrDiff NIM (L40S), Earth2Studio (data pipeline), Omniverse Kit (substation digital twin)

### Beat 2: Triage (0:45–1:15)

**What the customer sees**: A risk-ranked asset table appears alongside the map. Top 5 highest-risk assets are highlighted — three poles (wood, 20+ years old, last inspected 8 months ago, vegetation clearance marginal) and two transformer locations. Each row shows: asset ID, type, age, last inspection, vegetation clearance, weather exposure score, composite risk score, and a **score breakdown tooltip** showing the weighted contribution of each factor.

In the 3D substation view, Transformer T-008 shifts from green to amber — its risk score has crossed the warning threshold. If NV-Tesseract-AD is integrated, the transformer pulses: "Anomaly detected — oil temperature trend 2.3σ above baseline, predicted thermal stress under forecast ice loading."

The narrator: "The system isn't just looking at weather — it's combining four risk dimensions to prioritize where to look first. And every score is explainable — your dispatcher can see exactly why this pole ranked highest. You can see the transformer in the digital twin has gone amber — the same data, rendered in 3D."

**What's happening technically**: The Risk Engine computed scores using a weighted formula across four dimensions. The console backend proxies the ranked asset list from the Risk Engine's REST API. The asset database contains seeded but realistic data for ~100 assets in the corridor. Each asset score includes a breakdown of the four sub-scores for explainability. The Kit extension receives the risk score update for T-008 via Kafka and updates the transformer's material color in the 3D scene.

**NVIDIA products**: Omniverse Kit (data-driven material update). NV-Tesseract-AD could augment this with time-series anomaly detection on transformer telemetry — see Section 3.5.

### Beat 3: Escalate Monitoring (1:15–1:45)

**What the customer sees**: The top-priority assets are flagged. Camera icons appear on the map at those locations — pole-mounted cameras and substation security cameras already deployed in the corridor. An "Escalate Monitoring" action triggers: camera analysis frequency increases from hourly baseline to every 30 seconds on the 5 priority assets. Camera feed panels begin appearing in the right panel, cycling through the live views. The narrator: "These cameras are already installed — substation security cameras, pole-mounted units for vegetation monitoring. The system just increased analysis frequency on the assets the risk engine flagged. No crew dispatched yet. AI is inspecting remotely, watching 50+ feeds simultaneously — something no human operator can do."

**Narrator note (edge)**: "In production, Cosmos Reason runs on NVIDIA Jetson Orin modules co-located with these cameras at the substation or on the pole. Defects are detected at the edge in real-time — only alerts travel back to the operations center. Edge devices run RHEL with the NVIDIA GPU stack, managed at scale by Red Hat Edge Manager — OS updates, model deployments, and device lifecycle all from a single control plane."

**What's happening technically**: The Scenario Engine emits a CAMERA_ESCALATE event to Kafka with the list of priority asset camera IDs. The Camera Simulator increases its frame publication rate on `grid.cameras.frames` for those cameras. Pre-staged images (weather-augmented via Cosmos Transfer 2.5 at build time) are streamed at the escalated interval. The console renders camera icons on the map at fixed positions and cycles through feeds in the camera panel.

**NVIDIA products**: Cosmos Transfer 2.5 (weather augmentation of camera imagery, pre-processed at build time)

### Beat 4: Detect (1:45–2:30)

**What the customer sees**: The camera feed from the pole-mounted camera at P-037 shows the crossarm in frame. Cosmos Reason processes the image — an alert card appears beside the camera feed: "DEFECT: Cracked crossarm — severity CRITICAL, confidence 0.91" with Cosmos Reason's natural language description: *"Longitudinal crack visible on the crossarm, approximately 30cm from the pole attachment point. Recommend immediate replacement before ice loading."* The feed cycles to the camera covering spans near P-052. A second alert: "HAZARD: Vegetation encroachment — severity MAJOR, confidence 0.87" — *"Tree canopy within approximately 1.5 meters of the conductor on two adjacent spans."* Both findings appear in the event stream with trace IDs linking back to the weather forecast that triggered the escalated monitoring.

The narrator: "No crew was dispatched to find these. The cameras were already there — the AI just started watching more carefully when the weather forecast flagged these assets. It's describing what it sees — the same way a field engineer would radio in a finding. That cracked crossarm would have failed under ice loading tonight. Now we know about it 14 hours before the storm hits."

**What's happening technically**: The Defect Detector service consumes frames from `grid.cameras.frames`, sends each to Cosmos Reason 2-8B (via vLLM), and parses the VLM's structured response. Cosmos Reason observes the image and answers questions about what it sees — it produces natural language descriptions and defect classifications, not visual annotations or bounding boxes. The console displays findings as text alert cards alongside the camera feed image. For production, a complementary detection model (YOLO or Grounding DINO) could add visual bounding box overlays on the image — but the demo's value is in Cosmos Reason's ability to describe and classify what it observes in domain-specific language. Findings are published to `grid.cameras.findings`.

**NVIDIA products**: Cosmos Reason 2-8B via vLLM (L40S)

### Beat 5: Crew Dispatch + Dispatcher Approval (2:30–3:15)

**What the customer sees**: The camera-detected findings automatically generate work orders. A **"Dispatcher Review" panel** appears showing the AI-recommended dispatch plan: 8 crews on shift, each with skill badges (lineman, vegetation, substation tech). cuOpt has computed optimal assignments. The dispatcher sees the full recommendation — crew assignments, routes, ETAs — and has the option to **approve, modify, or override** any assignment. The narrator clicks "Approve All." Animated route lines appear on the map showing crew paths to their assigned work sites. A dispatch summary panel shows: Crew 3 (vegetation, ETA 22 min) → spans with encroachment. Crew 7 (lineman, ETA 35 min) → Pole P-037 crossarm replacement. The narrator: "cuOpt solved this in 200 milliseconds — skills, proximity, shift constraints, priority, all optimized simultaneously. But the dispatcher always has final authority. This is decision support, not autonomous dispatch."

**Narrator note (scale)**: "We're showing 8 crews here. In a real ice storm, utilities mobilize hundreds to thousands of crews including mutual aid. cuOpt is GPU-accelerated and designed for large-scale fleet optimization — the solve time stays sub-second as the problem grows."

**What's happening technically**: The Work Order Generator creates work orders from camera-detected findings, each tagged with required skills, priority, and location. Work orders pass through a **NeMo Guardrails safety check** that validates: (1) no crew is dispatched to a zone with active un-isolated faults, (2) crew certifications match work requirements, (3) shift time remaining is sufficient for the assigned work. The Dispatch Optimizer calls cuOpt with the full problem. Results enter a "pending approval" state. On dispatcher approval (or auto-approval in demo mode), dispatch assignments are published to `grid.crew.dispatch` and rendered on the map.

**NVIDIA products**: cuOpt (VRP with skill matching, time windows, priorities), NeMo Guardrails (safety validation)

### Beat 6: Storm Response (3:15–4:15)

**What the customer sees**: Time advances. The weather overlay intensifies — ice accumulation hits the forecast peak. A **customer impact banner** appears at the top: monitoring 12,400 customers on these feeders.

A fault indicator flashes on the map: "FAULT DETECTED — Feeder F-12, segment between P-051 and P-052." The affected feeder section dims. In the 3D substation view, the circuit breaker for F-12 visually trips — equipment state changes to red. **AMI last-gasp signals** confirm: "847 customers without power." The ETR counter begins: "Estimated restoration: calculating..."

An **ADMS verification panel** briefly appears: "Receiving feeder F-15 capacity check: 4.2 MW available / 3.1 MW transfer load — CLEAR. Tie switch TS-04 close command authorized." The alternate path illuminates green on the map. In the 3D view, the tie switch visually closes — the equipment state transitions from open to closed.

Updated impact: "847 customers affected → 312 restored via automatic switching. 535 remaining. ETR: 2h 15m."

Two new fault-response work orders appear (fault investigation, line repair — priority CRITICAL). cuOpt re-optimizes: crew routes animate re-routing on the map in real-time. One crew is redirected from a lower-priority vegetation job to the fault location. The dispatcher approval panel flashes — storm-mode auto-approval is active for critical work orders.

**Narrator**: "The storm hit, a line went down, 847 customers lost power. You saw the breaker trip in the digital twin. Automatic switching restored 312 immediately — you saw the tie switch close. cuOpt re-optimized every crew route in under a second. The dispatcher approved the critical re-routes in storm-priority mode. And every decision — the switching, the re-routing, the approval — is fully traceable for your regulatory filings."

**What's happening technically**: The Scenario Engine triggers a fault event on a pre-determined feeder segment. The system emits a `grid.faults.detected` event with the faulted segment and customer count. The Kit extension receives the fault event via Kafka and updates the breaker equipment material to red/emissive in the 3D scene. AMI last-gasp events (simulated) confirm customer outages on `grid.ami.outages`. A simulated ADMS capacity verification step runs before the switching action — this is narrated/displayed, not a real load-flow calculation, but the console shows the capacity check result to demonstrate awareness of the operational requirement. The restoration event follows — the Kit extension updates the tie switch state in the 3D scene. New work orders are created at highest priority. The Dispatch Optimizer re-runs cuOpt with the updated work order set. In storm mode, the dispatcher approval step auto-approves critical work orders (configurable).

**NVIDIA products**: Omniverse Kit (fault/switching visualization in digital twin), cuOpt (re-optimization with updated constraints)

### Beat 7: Trace, Platform & Close (4:15–5:00)

**What the customer sees**: A full event timeline unfolds vertically: Earth-2 forecast → risk scoring → camera escalation → AI defect detection (remote, no crew on-site) → work order creation → dispatcher approval → crew dispatch to repair → storm arrival → AMI outage detection → ADMS capacity check → automatic switching → customer restoration → crew re-optimization → repair arrival. Each event is linked by trace ID.

The 3D substation view — which has been live alongside the map since the demo started — now shows the full state: transformer T-008 amber (pre-storm risk), breaker for F-12 red (tripped), tie switch TS-04 closed (restoration). Every state change the customer watched happen in real-time is still visible as evidence.

The console briefly shows a **"Platform" tab** with three panels:
1. **OpenShift topology view**: All services healthy, GPU Operator managing L40S nodes + Kit rendering, AMQ Streams Operator managing Kafka
2. **Argo CD sync status**: All applications synced and healthy
3. **Observability snapshot**: GPU utilization chart showing the CorrDiff inference spike, Cosmos Reason inference latency, cuOpt solve times, Kit rendering GPU — Kafka consumer lag all zero

**Narrator**: "Every decision is traceable — from the weather model that triggered the escalated camera monitoring, to the AI that found the damage remotely, to the optimizer that routed the crew. Full lineage, full auditability for your rate case filings and regulatory proceedings. And every component — from the AI models to the message bus to the database — is deployed, monitored, and upgraded through OpenShift Operators and GitOps. Your team manages the entire stack through a single control plane."

**Value metrics displayed on closing card**:
- Forecast lead time: 18 hours (vs. industry average 6 hours)
- Pre-storm defects found: 3 (would have caused additional outages)
- Crew dispatch optimization: 31% reduction in total travel time vs. nearest-available assignment
- Automatic switching restoration: 312 customers restored in <30 seconds
- cuOpt solve time: 200ms (supports 1,000+ crews at scale)
- Full decision lineage: every action auditable for regulatory filings

**NVIDIA products**: Omniverse Kit (substation digital twin rendering + WebRTC streaming)

**Closing note**: "In a production deployment, this connects to your existing systems — your GIS for asset data, your work management system for work orders, your SCADA/EMS for real-time grid state, and your workforce management system for crew dispatch. The AI layers sit alongside your existing operations systems, not replace them. And it all runs on-premise, behind your firewall, on OpenShift — no grid data leaves your network."

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     OPERATIONS CONSOLE                           │
│  ┌─────────────────────────┬────────────────────────────────┐   │
│  │                         │  3D Substation Digital Twin     │   │
│  │      MAP VIEW           │  (Omniverse Kit WebRTC)        │   │
│  │  - Weather overlay      │  - Equipment risk colors       │   │
│  │  - Asset markers        │  - Breaker/switch state        │   │
│  │  - Feeder lines         │  - Fixed camera angle          │   │
│  │  - Crew routes          ├────────────────────────────────┤   │
│  │  - Fault indicators     │  Context Panel (cycles):       │   │
│  │                         │  Forecast / Camera Feeds /     │   │
│  │                         │  Dispatch / Event Stream       │   │
│  └─────────────────────────┴────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Controls [Start] [Advance] [Storm] [Fault] [Reset]  0.2s   │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │ SSE (events) + REST (state)
┌──────────────────────────────┴───────────────────────────────────┐
│                      CONSOLE BACKEND (BFF)                        │
│                    FastAPI + Uvicorn (Python)                      │
└──────────────────────────────┬───────────────────────────────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        │          │           │           │          │
 ┌──────▼───┐ ┌───▼──────┐ ┌─▼────────┐ ┌▼───────┐ ┌▼──────────┐
 │ Weather  │ │ Risk     │ │ Dispatch │ │Safety  │ │ Cosmos    │
 │ Service  │ │ Engine   │ │ Optim.   │ │Guards  │ │ Transfer  │
 │          │ │          │ │          │ │        │ │ Service   │
 │ Earth2   │ │ scoring  │ │ cuOpt    │ │ NeMo   │ │ weather   │
 │ Studio + │ │ logic +  │ │ (REST)   │ │ Guard- │ │ augment.  │
 │ CorrDiff │ │ asset DB │ │          │ │ rails  │ │ of imgs   │
 │ NIM      │ │          │ │          │ │        │ │           │
 └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬───┘ └─────┬─────┘
      │            │            │            │           │
      ▼            ▼            ▼            ▼           ▼
 ┌──────────────────── Kafka (AMQ Streams) ────────────────────┐
 │  grid.weather.forecast    grid.crew.work-orders              │
 │  grid.weather.alerts      grid.crew.dispatch                 │
 │  grid.assets.risk-scores  grid.crew.telemetry                │
 │  grid.cameras.escalate    grid.faults.detected               │
 │  grid.cameras.frames      grid.faults.restoration            │
 │  grid.cameras.findings    grid.ami.outages                   │
 │  grid.ops.events          grid.customer.impact               │
 └──────────────────────┬──────────────────────────────────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
┌──────▼───────┐ ┌──────▼───────┐ ┌──────▼───────┐
│ Camera       │ │ Defect       │ │ Scenario     │
│ Simulator    │ │ Detector     │ │ Engine       │
│              │ │              │ │              │
│ pre-staged   │ │ Cosmos       │ │ scripted     │
│ camera       │ │ Reason 2-8B  │ │ demo events  │
│ frames →     │ │ via vLLM     │ │ + AMI sim    │
│ Kafka        │ │ (L40S)       │ │ + fault sim  │
└──────────────┘ └──────────────┘ └──────────────┘

Note: Cosmos Transfer 2.5 runs at build time (pre-processing imagery),
not as a runtime service.
```

---

## 3. NVIDIA Product Integration Details

### 3.1 Earth-2: Weather Forecasting

**Products used**: CorrDiff NIM + Earth2Studio Python framework

**How it works**:

1. **Data acquisition**: Earth2Studio fetches GFS/GEFS initial conditions from NOAA (or pre-staged NetCDF files for offline demo). GFS provides global atmospheric state at 0.25° (~25km) resolution, updated every 6 hours.

2. **Global forecast** (optional, adds fidelity): FourCastNet/SFNO produces a 15-day global forecast at 25km. The FourCastNet NIM is optimized for H100/B200 and is not listed in the L40S-supported profiles. Two options:
   - Use the **hosted API** at build.nvidia.com (requires network)
   - Run FourCastNet via **Earth2Studio directly** (not the NIM) — proven on 16GB A10G GPUs by DTN; works on L40S with controlled batch sizes
   - **For demo reliability**: pre-compute and cache the global forecast. Display it as real output.

3. **Regional downscaling**: CorrDiff NIM downscales from 25km to **3km over CONUS**. This NIM is **explicitly supported on L40S (48GB)**. Input: GEFS ensemble data (NumPy arrays). Output: 8 variables (u10m, v10m, t2m, tp, csnow, cicep, cfrzr, crain) at 3km grid spacing.
   - At 3km, the Piedmont NC corridor will have **multiple grid cells** covering it — sufficient resolution to show differential weather impact across the corridor.
   - Inference latency on L40S: low single-digit seconds per timestep (slower than H100 due to memory bandwidth, but fast enough).

4. **Demo pipeline**:
   ```
   Pre-staged GFS data (or live fetch)
     → FourCastNet via Earth2Studio (global, 25km) [pre-computed for demo]
     → CorrDiff NIM (CONUS, 3km) [live inference on L40S — the impressive part]
     → Extract Piedmont NC grid cells
     → Publish to grid.weather.forecast Kafka topic
     → Console renders on map
   ```

5. **Weather variables for risk scoring**:
   - `t2m` (2m temperature): below freezing → ice accumulation risk
   - `u10m/v10m` (10m wind): high wind → structural stress on poles/lines
   - `cfrzr` (freezing rain): boolean — primary ice storm indicator for Piedmont NC
   - `tp` (total precipitation): combined precipitation load in mm
   - Derived: `ice_accumulation_mm = tp_mm * ICE_DENSITY_FACTOR if cfrzr else 0.0` where `ICE_DENSITY_FACTOR ≈ 0.85` accounts for glaze ice density vs. water equivalent (per Goodwin-Mozer ASCE standard)
   - Derived: `wind_on_ice_load_N = 0.5 * air_density * wind_speed² * ice_diameter * span_length` (Overturning Moment calculation for poles)

**Key risk**: First CorrDiff inference is slow (dynamic compilation warm-up, 2-3 inferences). Mitigation: warm up the NIM before the demo starts; or pre-compute results and display as-if-live with a toggle for actual live inference.

**Container**: `nvcr.io/nim/nvidia/corrdiff:1.1.0` — pull from NGC with API key. Pin to a specific version tag.

### 3.2 cuOpt: Crew Dispatch Optimization

**Product used**: cuOpt — open source, Apache 2.0 (no NVIDIA AI Enterprise license required)

cuOpt was open-sourced at GTC 2025. It is distributed as a standard container on Docker Hub (`nvidia/cuopt`), not as a NIM from `nvcr.io`. The container tag format includes Python version: e.g., `nvidia/cuopt:26.06-cuda12.9-py3.13`.

**How it works**:

cuOpt solves the Vehicle Routing Problem with constraints. For this demo, it handles crew dispatch and re-optimization:

**Crew dispatch (Beat 5, Beat 6)**:
- Multiple vehicles (8 crews), multiple tasks (4-6 work orders), skill matching, time windows, priorities
- Full CVRPTW with skill constraints
- Called once for initial dispatch (Beat 5) and again for re-optimization when storm faults create new work orders (Beat 6)

**Input/output format**: The cuOpt REST API at port 5000 (`/cuopt/request`) accepts JSON with `cost_matrix_data`, `fleet_data`, `task_data`, and `solver_config` top-level keys. Skill-based matching uses `vehicle_order_match` / `order_vehicle_match` fields. **These field names must be validated against the current 26.x open-source API before implementation** — the transition from proprietary NIM to open-source server may have introduced schema changes. Build a test script early in Phase B.

**Re-optimization (Beat 6)**: When the storm triggers a fault, new work orders are created at higher priority. The Dispatch Optimizer re-submits the full problem to cuOpt with updated crew locations, completed/in-progress work orders, and new fault-response work orders. cuOpt re-solves in sub-second, potentially reassigning a crew from a lower-priority task to the fault.

**Cost matrix generation**: For demo scale (8 crews, ~10 locations), use pre-computed road distances via OSRM or Euclidean. OSRM can be containerized (`osrm/osrm-backend`) with North Carolina road data (from OpenStreetMap). A 10x10 matrix computes in milliseconds.

**Container**: `nvidia/cuopt:26.06-cuda12.9-py3.13` from Docker Hub. REST API at port 5000. Apache 2.0 — free for all use including commercial.

### 3.3 Cosmos Reason: Defect Detection

**Product used**: Cosmos Reason 2-8B (Qwen3-VL derivative) via vLLM

**How it works**:

Same serving architecture as the warehouse obstruction detector — vLLM serves the model on L40S, the Defect Detector service sends image+prompt requests via the OpenAI-compatible chat completions API.

**Prompt design** (critical for demo quality):
```
You are a utility infrastructure monitoring AI. You are observing
a frame from a fixed camera mounted on distribution grid infrastructure.

Examine the image and answer: are any of the following conditions present?
- Cracked, broken, or split crossarms
- Damaged or missing insulators
- Vegetation within 3 meters of conductors
- Leaning or tilted poles
- Missing hardware (bolts, clamps, guy wire attachments)
- Visible corrosion on metal components
- Animal nests or debris on equipment
- Ice accumulation on conductors or equipment

For each condition observed, respond with JSON:
{
  "findings": [
    {
      "defect_type": "cracked_crossarm",
      "severity": "critical",
      "confidence": 0.91,
      "description": "Longitudinal crack visible on the crossarm, approximately 30cm from the pole attachment point. Crack runs parallel to the grain and appears to extend through the full depth of the crossarm.",
      "recommended_action": "REPLACE - schedule lineman crew before ice loading event"
    }
  ]
}

If no conditions are observed, return: {"findings": []}
```

**Observation model, not annotation model**: Cosmos Reason observes images and answers questions about what it sees — it produces natural language descriptions and structured classifications. It does not produce visual annotations, bounding boxes, or region highlights. The demo displays findings as text alert cards beside the camera feed. For production deployments requiring visual overlays on imagery, a complementary detection model (YOLO or Grounding DINO on a Jetson at the camera site or on the hub) would provide bounding boxes alongside Cosmos Reason's natural language assessment.

**Imagery source**: 10-15 curated images representing fixed camera perspectives — pole-top looking at crossarms, substation security camera views, span-level cameras monitoring vegetation clearance (see Section 10). Published to Kafka by the Camera Simulator at scripted intervals synchronized with the escalated monitoring scenario.

**vLLM serving config**:
```bash
vllm serve nvidia/Cosmos-Reason2-8B \
  --reasoning-parser qwen3 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 16384
```
Requires vLLM >= 0.11.0. Single-GPU only (TP=1).

**Fallback for unreliable VLM observation**: If Cosmos Reason cannot reliably identify defects in the curated image set after prompt iteration, fall back to a hybrid approach: use a fine-tuned YOLO model for defect detection (visual bounding boxes + binary classification) and Cosmos Reason for natural language description and severity assessment of what YOLO detected. Both models doing real inference — technically honest.

### 3.4 Cosmos Transfer 2.5: Weather Augmentation of Camera Imagery

**Product used**: Cosmos Transfer 2.5 (Image2Image generation)

**Role in the demo**: Featured, not optional. Cosmos Transfer 2.5 transforms clear-weather camera images into storm-condition versions — adding overcast sky, ice accumulation on conductors, wet/icy pole surfaces, low-visibility conditions. This serves two purposes:

1. **Visual credibility**: Camera images that match the storm scenario look more realistic than clear-sky photos during an ice storm demo.
2. **NVIDIA product showcase**: Adds a fourth NVIDIA inference product to the demo (fifth counting NeMo Guardrails).

**How it works**:
- Base images sourced from public datasets or purpose-shot photography (clear weather)
- Cosmos Transfer 2.5 applies weather conditioning: `{weather: "overcast, ice accumulation, freezing rain"}` + `{lighting: "twilight, overcast"}` + `{surface: "ice, frost"}`
- Pre-process the full image set during build time (not live during demo)
- Store both original and weather-augmented versions; the Camera Simulator selects the weather-augmented set during the ice storm scenario

**Container**: Available from NGC. The Cosmos Cookbook includes a recipe for weather augmentation of infrastructure images ("ITS Weather Augmentation").

### 3.5 NV-Tesseract-AD: Predictive Asset Anomaly Detection (Natural Fit)

**Product used**: NV-Tesseract-AD NIM

**Role in the demo**: Enhances Beat 2 (Triage). While the Risk Engine uses a deterministic weighted scoring formula, NV-Tesseract-AD adds a learned anomaly detection layer for transformer assets that have time-series telemetry (oil temperature, load current, partial discharge).

**How it fits**:
- During Beat 2, one of the priority assets (T-008, a pad-mount transformer) is flagged not just by the deterministic risk score but by NV-Tesseract-AD detecting an anomalous temperature trend in its recent telemetry.
- The console shows: "Transformer T-008: Risk score 0.84 (weather + age). NV-Tesseract anomaly: oil temperature trend 2.3σ above baseline — predicted thermal stress under forecast ice loading."
- This adds a "the AI sees something the formula alone would miss" moment.

**Integration**: NV-Tesseract-AD NIM consumes time-series data (simulated transformer telemetry published to Kafka) and produces anomaly scores. The Risk Engine incorporates the anomaly score as an additional factor for transformer assets. Demonstrated at CERAWeek 2026 for exactly this kind of industrial sensor anomaly detection.

**Scope**: This is a natural fit enhancement, not a core dependency. If NV-Tesseract-AD integration adds too much build complexity, it can be deferred to a Phase 2 demo expansion without breaking the core narrative.

### 3.6 NeMo Guardrails: Safety Validation for Crew Dispatch

**Product used**: NeMo Guardrails (open-source, Apache 2.0)

**Role in the demo**: Validates crew dispatch recommendations before execution. Sits between cuOpt output and dispatcher approval.

**Safety checks**:
1. No crew dispatched to a zone with active un-isolated faults
2. Crew certifications match work order requirements (e.g., hot-stick certified for energized line work)
3. Remaining shift time sufficient for assigned work + travel
4. No crew dispatched into an active weather red-zone without storm-duty authorization

**Integration**: Lightweight — NeMo Guardrails validates the cuOpt dispatch plan as a post-processing step. If a violation is detected, the plan is flagged and the dispatcher sees a warning. This is not computationally expensive and does not require a GPU.

### 3.7 Edge Inference Narrative (Jetson)

Narrated during Beat 3 and available as a talking point. The fixed-camera model makes this story more natural than a drone model — cameras at substations and on poles are permanently installed, co-located with a Jetson module for local inference:

"In production, Cosmos Reason runs on NVIDIA Jetson Orin modules co-located with these cameras at the substation or on the pole, using an FP8-quantized checkpoint. Defects are detected at the edge in real-time — only alerts travel back to the operations center, not raw video. This reduces bandwidth requirements by 99% and keeps latency under 2 seconds. Edge devices run RHEL with the NVIDIA GPU stack, managed at scale by Red Hat Edge Manager — OS provisioning, model updates, security patching, and device lifecycle for hundreds of substation edge nodes from a single console."

This connects NVIDIA's cloud-to-edge story with Red Hat's edge management narrative. RHEL on Jetson is the runtime; Edge Manager handles fleet lifecycle (enrollment, OS image updates, configuration drift, health monitoring). The fixed-camera + edge-inference architecture follows a validated industry pattern — several vendors already ship substation camera analytics on Jetson using Metropolis/DeepStream.

### 3.8 Omniverse Kit: Substation Digital Twin

**Product used**: NVIDIA Omniverse Kit + Kit App Streaming (WebRTC)

**Role in the demo**: A 3D substation digital twin rendered by Omniverse Kit, streamed into the console via WebRTC. Equipment in the scene changes color/emissive state based on risk scores and fault status from the same Kafka data pipeline that drives the map. This adds Omniverse — NVIDIA's flagship platform — to the demo, proving Red Hat can run Omniverse workloads on OpenShift.

**Where it appears**: Console has a "Substation" tab showing the 3D viewport alongside the map. During Beat 2 (Triage), the transformer in the scene shifts from green to amber as its risk score climbs. During Beat 6 (Storm Response), the faulted equipment pulses red with emissive glow. The scene provides spatial context that the 2D map cannot — "this is the physical equipment the data represents."

**Scene asset strategy — dual quality tiers**:

The Kit app loads whichever scene is present at startup. Two tiers:

| Tier | Source | Quality | Repo | Container |
|------|--------|---------|------|-----------|
| **High** (primary, for demos) | Purchased from Fab (~$30-$70), "Electrical Utility and Substation" or "Electrical Substation / 34 Assets" pack. PBR materials, pre-assembled scene, realistic. | Professional | Assets in `.gitignore`, NOT committed. `ASSETS.md` documents procurement. | Baked into private container image on Quay. |
| **Standard** (fallback, for open-source) | Code-generated via USD Python API (`usd-core`). Primitives (Cube, Cylinder) with CC0 PBR materials from Poly Haven (painted steel, concrete, gravel, porcelain). | Adequate for development/CI | Fully committed to public repo. Generator script + CC0 textures. | Baked into public container image on Quay. |

The Kit app selects the scene based on `SCENE_QUALITY` env var (`high` or `standard`). Both scenes have the same prim hierarchy (`/Substation/Transformer_01`, `/Substation/CircuitBreaker_01`, etc.) so the data-driven Kit extension works identically with either.

**Development approach**: Build and develop against the high-quality purchased scene throughout the project. Circle back in Phase E to build the CC0 standard-quality scene generator as a fallback for the open-source repo.

**High-quality asset workflow**:
1. Purchase pack from Fab (Fab Standard License — cross-engine use explicitly permitted, USD export allowed)
2. Export to FBX from Unreal/source tool
3. Convert FBX → USD via Omniverse Asset Converter
4. Arrange scene, set up material paths, verify in USD Composer
5. Store raw assets in private S3 or `.gitignore`'d local directory
6. Containerfile copies assets during build, bakes into Kit app data directory
7. Push built image to private Quay registry

**Standard-quality scene generator** (Phase E):
- Python script using `usd-core` (`pip install usd-core`)
- Equipment from `UsdGeom.Cube` (transformer bodies, control houses) + `UsdGeom.Cylinder` (bushings, insulators, bus bars, fence posts)
- CC0 PBR textures from Poly Haven: painted steel (green/grey), bare metal, concrete, gravel, porcelain
- `UsdPreviewSurface` materials with albedo, roughness, metallic, normal maps
- Same prim hierarchy as the purchased scene — Kit extension code works unchanged
- Committed to repo: `kit-substation/scene-generator/generate_substation.py` + `textures/`

**Licensing summary**:
- **Fab Standard License**: Demo at trade shows YES. Marketing screenshots YES. Public git repo for raw assets NO. Private Quay container YES. Cross-engine USD export YES.
- **CC0 textures (Poly Haven)**: All uses permitted, no restrictions, no attribution required.
- **Code-generated geometry**: Our IP, no restrictions.

**Kit App integration** (reference code from existing warehouse showcase):
- Kit App Streaming via WebRTC using `@nvidia/omniverse-webrtc-streaming-library` — pattern already proven in warehouse showcase, copy and adapt
- Custom Kit extension consumes Kafka events and modifies scene:
  - Risk score updates → equipment material color (green/yellow/orange/red gradient)
  - Fault events → pulsing red emissive glow on affected equipment
  - Restoration events → return to normal state
- Extension uses `omni.usd` API to modify `UsdPreviewSurface` shader attributes (`diffuseColor`, `emissiveColor`, `emissiveIntensity`)
- Streaming config: `local` mode for demo (direct WebRTC to Kit on LAN), no Kubernetes streaming infrastructure needed

**Container architecture**:
```
PUBLIC (Quay)                           PRIVATE (Quay)
kit-substation:standard                 kit-substation:high
├── Kit runtime + extensions            ├── Kit runtime + extensions
├── CC0 scene (generated primitives)    ├── Purchased scene (Fab asset, baked)
├── CC0 PBR textures                    ├── PBR textures from asset pack
└── Data-driven extension               └── Data-driven extension
    (identical code in both)                (identical code in both)
```

---

## 4. OpenShift Platform Architecture

### 4.1 Namespace Topology

```
grid-ops-infra        — AMQ Streams (Kafka), Crunchy PGO (PostgreSQL), observability
grid-ops-ai           — CorrDiff NIM, vLLM (Cosmos Reason), cuOpt, Kit (GPU workloads)
grid-ops-services     — Weather Service, Risk Engine, Dispatch Optimizer, etc.
grid-ops-console      — Console backend + frontend
grid-ops-monitoring   — User Workload Monitoring, Grafana dashboards
```

### 4.2 GPU Operator and Scheduling

- **NVIDIA GPU Operator** (from OperatorHub) manages drivers, device plugins, DCGM Exporter, and GPU Feature Discovery
- **Node Feature Discovery (NFD) Operator** — prerequisite for GPU Operator to label GPU nodes
- GPU nodes tainted with `nvidia.com/gpu=present:NoSchedule` — only GPU workloads scheduled there
- Pod resource requests: `nvidia.com/gpu: 1` per NIM pod
- GPU class targeting via native GFD labels: `nvidia.com/gpu.product: NVIDIA-L40S`

### 4.3 RBAC

- ServiceAccount per service (least privilege)
- `Role` per namespace granting only required API access
- `RoleBinding` connecting ServiceAccounts to Roles
- Console backend ServiceAccount has read access to `grid-ops-services` namespace for proxying

### 4.4 SecurityContextConstraints

- All custom services: `restricted-v2` SCC (non-root, read-only rootfs, dropped capabilities)
- NIM containers (CorrDiff, vLLM): `nvidia-gpu` SCC (created by GPU Operator, grants device access)
- cuOpt: `restricted-v2` if running on CPU; `nvidia-gpu` if on GPU

### 4.5 Networking

- **Default-deny NetworkPolicy** per namespace
- Explicit allow-list between services:
  - `grid-ops-services` → `grid-ops-infra` (Kafka, PostgreSQL)
  - `grid-ops-services` → `grid-ops-ai` (NIM endpoints)
  - `grid-ops-console` → `grid-ops-services` (API proxying)
  - `grid-ops-console` → `grid-ops-infra` (Kafka for SSE)
- Console Route with `haproxy.router.openshift.io/timeout: 300s` for SSE long-lived connections
- All east-west traffic over cluster network (Service Mesh optional for mTLS — documented as production enhancement)

### 4.6 Secrets Management

- **External Secrets Operator** or **Sealed Secrets** for GitOps-compatible secret management
- Secrets: NGC API key (ImagePullSecret for NIM containers), PostgreSQL credentials, Kafka SCRAM credentials, MapLibre/Mapbox API key
- NIM containers pulled via ImagePullSecret referencing NGC registry credentials

### 4.7 Container Images

- All custom services built on **UBI9** base images (`registry.access.redhat.com/ubi9/python-312`)
- NIM containers mirrored from `nvcr.io` to **Red Hat Quay** internal registry — scanned with Clair before deployment
- Container image signing with **cosign** via Tekton Chains
- SBOM generation with **Syft** (SPDX JSON) per image

---

## 5. Observability Architecture

### 5.1 Metrics

- **User Workload Monitoring** (OpenShift built-in Prometheus) with `ServiceMonitor` CRDs per service
- **DCGM Exporter** (automatic with GPU Operator) — GPU utilization, memory, temperature exposed to Prometheus
- Custom metrics per service:
  - Weather Service: `earth2_inference_duration_seconds`, `corrdiff_gpu_memory_bytes`
  - Defect Detector: `cosmos_reason_inference_latency_seconds`, `defects_detected_total`
  - Dispatch Optimizer: `cuopt_solve_time_seconds`, `cuopt_problem_size`, `dispatches_optimized_total`
  - Risk Engine: `assets_scored_total`, `risk_score_computation_seconds`
- **Grafana dashboard** (single dashboard): GPU utilization, Kafka consumer lag, cuOpt solve times, Cosmos Reason inference latency, service health

### 5.2 Logging

- **structlog** → JSON logs to stdout
- **OpenShift Logging** (Loki-based, OCP 4.14+) for log aggregation
- `ClusterLogForwarder` routes `grid-ops-*` namespace logs to Loki

### 5.3 Tracing

- **OpenTelemetry** instrumentation in all services
- **Red Hat build of OpenTelemetry** (Tempo Operator) for trace storage
- Trace IDs propagated through Kafka message headers — links the full event chain from forecast to crew dispatch
- Console event stream displays trace IDs; clicking a trace ID opens the Tempo UI

### 5.4 Alerting

- `PrometheusRule` CRDs:
  - CorrDiff inference latency > 10s
  - Cosmos Reason error rate > 5%
  - Kafka consumer lag > 100 messages
  - cuOpt solve failure

---

## 6. GitOps Architecture

### 6.1 Repository Structure

```
infrastructure/
  gitops/
    bootstrap/
      argocd-subscription.yaml      # Argo CD Operator subscription
      root-application.yaml         # Root App-of-Apps
    projects/
      grid-ops.yaml                 # Argo CD AppProject with RBAC
    applicationsets/
      grid-ops-infra.yaml           # Kafka, PostgreSQL, observability
      grid-ops-ai.yaml              # NIM deployments
      grid-ops-services.yaml        # Application services
      grid-ops-console.yaml         # Console frontend + backend
    overlays/
      dev/                          # Local dev values (resource limits, replicas)
      demo/                         # Demo environment (GPU scheduling, NIM endpoints)
```

### 6.2 Sync Policies

- Auto-sync enabled with self-heal and prune
- Wave ordering via `argocd.argoproj.io/sync-wave` annotations:
  - Wave 0: Operators (GPU Operator, AMQ Streams, Crunchy PGO)
  - Wave 1: Infrastructure (Kafka cluster, PostgreSQL cluster, Tempo)
  - Wave 2: AI workloads (NIM deployments)
  - Wave 3: Application services
  - Wave 4: Console

### 6.3 CI/CD

- **OpenShift Pipelines (Tekton)** for container image builds
- Pipeline stages: build → test → scan (Clair) → sign (cosign/Tekton Chains) → push (Quay) → SBOM (Syft)
- Argo CD detects updated image tags and syncs

---

## 7. Security and Compliance

### 7.1 NERC CIP Awareness

This demo targets distribution-level operations (generally not subject to mandatory NERC CIP). However, large utilities apply CIP-adjacent controls to distribution systems as best practice. The architecture addresses:

- **CIP-005 (Electronic Security Perimeters)**: This system sits in the IT zone, not on the OT network. In production, SCADA data crosses the IT/OT DMZ via a data diode or OPC-UA gateway — the AI system never has direct OT network access.
- **CIP-007 (System Security Management)**: RBAC, audit logging via OpenTelemetry, container image signing, vulnerability scanning via Quay/Clair.
- **CIP-010 (Configuration Change Management)**: GitOps via Argo CD — every configuration change is a Git commit with audit trail.
- **CIP-013 (Supply Chain Risk Management)**: Container image provenance (Sigstore/cosign), SBOMs (Syft/SPDX), NIM containers mirrored and scanned before deployment.

### 7.2 Audit Trail

Every AI recommendation (risk scores, dispatch plans, switching verifications) is logged with:
- Timestamp, trace ID, requesting user/system
- Input data (what the model saw)
- Output recommendation (what the model suggested)
- Dispatcher action (approved, modified, overridden)
- Justification field (optional free-text from dispatcher)

This audit trail is designed for regulatory proceedings: rate case filings, prudency reviews, after-action storm reports.

---

## 8. Services — Detailed Specifications

### 8.1 Weather Service

**Purpose**: Produce Earth-2 weather forecasts and publish to Kafka.

**Tech**: Python 3.12+, FastAPI, earth2studio, confluent-kafka, httpx

**Endpoints**:
- `GET /healthz` — health check
- `GET /readyz` — readiness (NIM available, data loaded; checks CorrDiff NIM endpoint)
- `GET /forecast/current` — latest forecast for the corridor
- `POST /forecast/run` — trigger a new forecast run (or return pre-computed)

**Modes**:
- `live` — fetches current GFS data, runs CorrDiff NIM, produces real forecast
- `demo` — returns pre-computed forecast for the scripted scenario
- Mode controlled by `WEATHER_MODE` env var

**Kafka output**: Publishes to `grid.weather.forecast` and `grid.weather.alerts` (when thresholds exceeded)

### 8.2 Risk Engine

**Purpose**: Score every asset in the affected corridor by combining weather exposure with asset condition data.

**Tech**: Python 3.12+, FastAPI, psycopg3 (PostgreSQL via Crunchy PGO), confluent-kafka

**Scoring algorithm**:
```python
def compute_risk_score(asset: Asset, forecast: WeatherForecast) -> float:
    weather = weather_exposure_score(asset, forecast)
    age = age_score(asset)
    vegetation = vegetation_score(asset)
    inspection = inspection_recency_score(asset)

    return (
        0.40 * weather +
        0.25 * age +
        0.20 * vegetation +
        0.15 * inspection
    )
```

**Weather exposure sub-score**:
```python
def weather_exposure_score(asset: Asset, forecast: WeatherForecast) -> float:
    cell = nearest_grid_cell(asset.lat, asset.lon, forecast.grid_cells)
    wind_speed = math.sqrt(cell.u10m_mps**2 + cell.v10m_mps**2)

    wind_score = min(wind_speed / 30.0, 1.0)
    ice_accumulation = cell.total_precip_mm * ICE_DENSITY_FACTOR if cell.freezing_rain else 0.0
    ice_score = min(ice_accumulation / 25.0, 1.0)

    exposure_multiplier = 1.3 if asset.is_end_of_line else 1.0
    compound = min((wind_score * 0.4 + ice_score * 0.6) * exposure_multiplier, 1.0)

    return compound
```

Each score response includes a **breakdown** of the four sub-scores for UI explainability.

**Database**: PostgreSQL via **Crunchy PGO** (Red Hat Marketplace certified). Tables: `assets`, `inspections`, `risk_scores`, `feeders`, `segments`, `switches`, `crews`, `customers_per_segment`.

**Kafka**: Consumes `grid.weather.forecast`, publishes `grid.assets.risk-scores`

### 8.3 Camera Simulator

**Purpose**: Simulate fixed camera feeds by streaming pre-staged imagery to Kafka at configurable intervals.

**Tech**: Python 3.12+, FastAPI, confluent-kafka

- Holds a library of 10-15 curated camera images (base images + Cosmos Transfer weather-augmented variants)
- Each image is associated with a camera ID and its corresponding asset
- Baseline mode: publishes frames at low frequency (hourly) simulating routine monitoring
- Escalated mode: on receiving a `grid.cameras.escalate` event, increases frame rate to every 30 seconds for the specified cameras
- Streams images to `grid.cameras.frames` topic

### 8.4 Defect Detector

**Purpose**: Consume inspection imagery, run Cosmos Reason inference, publish structured findings.

**Tech**: Python 3.12+, FastAPI, confluent-kafka, httpx (for vLLM API)

- Consumes `grid.cameras.frames`
- Calls Cosmos Reason 2-8B via vLLM's OpenAI-compatible API
- Parses VLM response JSON (natural language descriptions and classifications)
- Publishes structured findings to `grid.cameras.findings`
- Creates work orders on `grid.crew.work-orders` for actionable findings

### 8.5 Dispatch Optimizer

**Purpose**: Consume work orders and crew state, validate through NeMo Guardrails, call cuOpt, publish dispatch assignments pending dispatcher approval.

**Tech**: Python 3.12+, FastAPI, confluent-kafka, httpx, nemoguardrails

**Flow**:
1. Assembles optimization problem from work orders + crew state
2. Calls cuOpt REST API
3. Passes cuOpt result through NeMo Guardrails safety checks
4. Publishes dispatch plan with `status: "pending_approval"` to `grid.crew.dispatch`
5. On dispatcher approval (via console), updates status to `approved` and publishes final assignments

**Re-optimization**: Triggered by new critical work orders, crew task completion, or periodic timer (every 60s during storm mode). Storm mode enables auto-approval for critical work orders.

### 8.6 Scenario Engine

**Purpose**: Script the demo narrative — emit events on button press or schedule to drive the demo flow predictably.

**Tech**: Python 3.12+, FastAPI, confluent-kafka

**Endpoints**:
- `GET /scenarios` — list available scenarios
- `POST /scenario/start` — begin the scripted demo
- `POST /scenario/advance` — advance to next beat
- `POST /scenario/trigger-storm` — trigger storm arrival
- `POST /scenario/trigger-fault` — trigger fault event with customer impact
- `POST /scenario/reset` — reset all state

**Scenario definition**: YAML files per geography/weather-type. The `ice_storm_piedmont.yaml` scenario defines beat progression, camera IDs to escalate, fault location, customer counts per segment, AMI simulation parameters, and ADMS capacity check results.

**AMI simulation**: When a fault fires, the Scenario Engine emits simulated AMI last-gasp events on `grid.ami.outages` with per-meter outage confirmations. The customer impact count is derived from the `customers_per_segment` table in the asset database.

### 8.7 Console Backend (BFF)

**Purpose**: Serve the frontend, proxy service APIs, stream Kafka events via SSE.

**Tech**: Python 3.12+, FastAPI, confluent-kafka, httpx

**Routes**:
```
GET  /healthz, /readyz
GET  /api/weather/current
GET  /api/assets, /api/assets/ranked, /api/assets/{id}
GET  /api/dispatch/current, /api/dispatch/crews
GET  /api/cameras/findings
GET  /api/customer-impact              → current outage count, ETR, affected segments
POST /api/dispatch/approve/{plan_id}   → dispatcher approval
POST /api/dispatch/override/{plan_id}  → dispatcher override with justification
GET  /api/scenario/current
POST /api/scenario/{action}
GET  /api/events                       → SSE stream of all Kafka events
GET  /api/topology                     → grid topology for map rendering
GET  /api/platform-status              → Argo CD sync, GPU utilization, service health
```

**SSE stream**: Consumes all `grid.*` Kafka topics and multiplexes events to the frontend. Route annotation: `haproxy.router.openshift.io/timeout: 300s`.

### 8.8 Console Frontend

**Purpose**: Operations center UI — the visual anchor of the entire demo.

**Tech**: React 19, TypeScript, Vite, MapLibre GL JS, PatternFly 6

**Why MapLibre over Mapbox**: MapLibre GL JS is the open-source fork of Mapbox GL JS (pre-proprietary-license-change). API-compatible, no proprietary license required. Self-hosted vector tiles via OpenMapTiles or Protomaps eliminate network dependency for air-gap/offline demos. For production, Mapbox can be swapped in via configuration if the customer prefers it.

**Layout** (single-page, tabs for different views):

**Primary view — Operations Console** (persistent split layout):
- **Left**: Map with asset markers (risk-coded), feeder lines (energized state), weather overlay, crew routes, fault indicators
- **Right top**: 3D substation digital twin (Omniverse Kit WebRTC viewport, fixed camera angle). Equipment colored by risk score / fault state, driven by same Kafka pipeline. Embedded via `@nvidia/omniverse-webrtc-streaming-library` — reference code from warehouse showcase.
- **Right bottom**: Contextual panel that cycles based on active beat — Forecast Summary, Camera Feeds (with AI finding cards), Dispatch Summary (with approval controls), Event Stream
- **Top banner**: Customer impact (outage count, ETR, customers restored) — appears during Beat 6
- **Bottom bar**: Scenario Controls + cuOpt solve time indicator

**Secondary view — Dispatcher Review** (shown during Beat 5):
- Full cuOpt dispatch recommendation with crew assignments, routes, ETAs
- Approve / Modify / Override controls per assignment
- NeMo Guardrails validation results (pass/warn/block per assignment)
- Justification text field for overrides (audit trail)

**Tertiary view — Platform Status** (shown during Beat 7):
- OpenShift topology view (service health)
- Argo CD sync status
- GPU utilization chart (DCGM metrics)
- Kafka consumer lag

**Optional view — Mobile Crew Mockup**:
- Simplified mobile-responsive view showing: current assignment, route to work site, next assignment, "Report Status" button, damage photo upload
- Not a full mobile app — a responsive view of the console demonstrating the field-crew experience
- Strengthens the dispatch story by showing both sides (control room + field)

---

## 9. Data Models

### 9.1 Asset Database (PostgreSQL via Crunchy PGO)

Extended schema addressing utility data complexity:

```sql
CREATE TABLE assets (
    id                      TEXT PRIMARY KEY,
    asset_type              TEXT NOT NULL,
    subtype                 TEXT,
    lat                     DOUBLE PRECISION NOT NULL,
    lon                     DOUBLE PRECISION NOT NULL,
    install_year            INTEGER,
    expected_lifespan_years INTEGER,
    feeder_id               TEXT REFERENCES feeders(id),
    is_end_of_line          BOOLEAN DEFAULT FALSE,
    vegetation_clearance_m  DOUBLE PRECISION,
    last_inspection_date    DATE,
    status                  TEXT DEFAULT 'in_service',
    -- Operationally meaningful fields (not all populated, but present in schema)
    rated_voltage_kv        DOUBLE PRECISION,
    phase_config            TEXT,         -- "3-phase", "1-phase-A", "1-phase-B"
    circuit_name            TEXT,
    protection_zone         TEXT,
    customers_downstream    INTEGER DEFAULT 0
);

CREATE TABLE feeders (
    id                  TEXT PRIMARY KEY,
    substation_id       TEXT,
    name                TEXT,
    normal_capacity_mw  DOUBLE PRECISION,
    current_load_mw     DOUBLE PRECISION,
    status              TEXT DEFAULT 'energized'
);

CREATE TABLE segments (
    id              TEXT PRIMARY KEY,
    feeder_id       TEXT REFERENCES feeders(id),
    from_asset_id   TEXT REFERENCES assets(id),
    to_asset_id     TEXT REFERENCES assets(id),
    conductor_type  TEXT,
    length_m        DOUBLE PRECISION,
    customers_served INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'energized'
);

CREATE TABLE switches (
    id                TEXT PRIMARY KEY,
    location_asset_id TEXT REFERENCES assets(id),
    from_feeder_id    TEXT REFERENCES feeders(id),
    to_feeder_id      TEXT REFERENCES feeders(id),
    state             TEXT DEFAULT 'open',
    transfer_capacity_mw DOUBLE PRECISION
);

CREATE TABLE cameras (
    id              TEXT PRIMARY KEY,       -- "CAM-P037", "CAM-SUB-A"
    camera_type     TEXT NOT NULL,          -- "pole_mounted", "substation_security", "span_monitor"
    asset_id        TEXT REFERENCES assets(id),
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    field_of_view   TEXT,                   -- "crossarm", "transformer_bank", "span", "perimeter"
    status          TEXT DEFAULT 'active',
    baseline_interval_seconds INTEGER DEFAULT 3600,
    escalated_interval_seconds INTEGER DEFAULT 30
);

CREATE TABLE crews (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    skills          TEXT[],
    certifications  TEXT[],      -- "hot_stick", "cdl", "bucket_truck"
    shift_start     TIME,
    shift_end       TIME,
    home_base_lat   DOUBLE PRECISION,
    home_base_lon   DOUBLE PRECISION,
    current_lat     DOUBLE PRECISION,
    current_lon     DOUBLE PRECISION,
    status          TEXT DEFAULT 'available'
);
```

### 9.2 Kafka Topics — Complete List

| Topic | Producer | Consumer(s) | Purpose |
|-------|----------|-------------|---------|
| `grid.weather.forecast` | Weather Service | Risk Engine, Console | Earth-2 forecast data |
| `grid.weather.alerts` | Weather Service | Risk Engine, Console | Threshold-based alerts |
| `grid.assets.risk-scores` | Risk Engine | Dispatch Optimizer, Console | Per-asset risk scores |
| `grid.cameras.escalate` | Scenario Engine | Camera Simulator | Escalate monitoring frequency on priority cameras |
| `grid.cameras.frames` | Camera Simulator | Defect Detector | Camera frames from fixed pole/substation cameras |
| `grid.cameras.findings` | Defect Detector | Dispatch Optimizer, Console | AI-detected defects from camera analysis |
| `grid.crew.work-orders` | Defect Detector, Scenario Engine | Dispatch Optimizer, Console | Work orders |
| `grid.crew.dispatch` | Dispatch Optimizer | Console | Dispatch assignments (pending/approved) |
| `grid.crew.telemetry` | Scenario Engine | Console | Crew location updates |
| `grid.faults.detected` | Scenario Engine | Dispatch Optimizer, Console | Fault events |
| `grid.faults.restoration` | Scenario Engine | Console | Switching/restoration events |
| `grid.ami.outages` | Scenario Engine | Console | AMI last-gasp outage confirmations |
| `grid.customer.impact` | Scenario Engine | Console | Customer outage count, ETR updates |
| `grid.ops.events` | All services | Console | Lifecycle events |

All topics provisioned as `KafkaTopic` CRs managed via GitOps (AMQ Streams Operator).

---

## 10. Camera Imagery Strategy

### Approach: Curated Fixed-Camera-Perspective Images + Cosmos Transfer 2.5 Weather Augmentation

**For the demo itself**, we need only 10-15 images representing what fixed cameras would capture. These are **not aerial/drone perspectives** — they are ground-level, pole-top, or substation-mounted camera views.

**Camera perspectives by type**:
- **Pole-mounted cameras**: Looking along the crossarm or down the span. Captures crossarm condition, insulator state, ice accumulation, conductor sag.
- **Substation security cameras**: Looking at transformer banks, switchgear, fencing, perimeter. Captures equipment condition, weather effects.
- **Span-monitoring cameras**: Looking along the conductor from one pole to the next. Captures vegetation clearance, conductor ice loading, sag.

**Image set**:

| # | Camera | Perspective | Cosmos Transfer augmentation | Expected finding |
|---|--------|-------------|------------------------------|------------------|
| 1 | CAM-P037 | Pole-top, looking at crossarm | Overcast sky, frost on surfaces | None (baseline) |
| 2 | CAM-P037 | Same camera, later frame | Ice buildup, frost | `cracked_crossarm`, critical |
| 3 | CAM-P041 | Pole-top, concrete crossarm | Overcast, light ice | None |
| 4 | CAM-P052 | Span monitor, looking along conductor | Overcast, wet vegetation | `vegetation_encroachment`, major |
| 5 | CAM-P052 | Same camera, adjacent span | Overcast, wet vegetation | `vegetation_encroachment`, major |
| 6 | CAM-SUB-A | Substation security, transformer bank | Wet ground, overcast | None |
| 7 | CAM-P063 | Pole-top, ice accumulation visible | Heavy ice on conductors | `ice_loading`, major |

**Sourcing**: Purpose-shot photography of residential distribution poles (ground-level perspective matching what a pole-mounted camera would see), utility substation security camera footage (widely available in public safety contexts), or public utility inspection datasets. The key difference from a drone-based approach: **eye-level or pole-height perspectives, not aerial**. Validated against Cosmos Reason detection accuracy before committing.

---

## 11. Integration Architecture (Production Path)

The demo runs standalone with synthetic data. In a production deployment, the integration points are:

| System | Protocol | Direction | What flows |
|--------|----------|-----------|------------|
| **Esri ArcGIS** (GIS) | REST API (Feature Service) | Inbound | Asset locations, attributes, connectivity model |
| **IBM Maximo / SAP PM** (WFM) | OSLC API / OData | Bidirectional | Work orders created by AI, status updates from field |
| **SCADA/EMS** (ABB, GE, OSI) | DNP3 / IEC 61850 via OPC-UA gateway | Inbound | Fault indicators, switch status, load measurements |
| **ADMS** (GE, Schneider, Oracle) | REST API / CIM | Bidirectional | FLISR commands, capacity checks, topology updates |
| **DTN / WSI** (weather) | REST API | Inbound | Commercial weather feeds (complementary to Earth-2) |
| **OMS** (Oracle, ABB) | REST API / MultiSpeak | Bidirectional | Customer outage data, ETR updates, crew status |
| **AMI** (Itron, Landis+Gyr) | Head-end REST API | Inbound | Last-gasp outage events, power-on confirmations |

The AI layers sit **alongside** the existing ADMS/OMS, not as a replacement. The value is in the predictive and optimization capabilities that existing systems lack.

---

## 12. Real vs. Stubbed — Honest Analysis

| Component | Real or Stubbed | Notes |
|-----------|----------------|-------|
| **Earth-2 CorrDiff** | **Real inference** | Live on L40S with pre-computed fallback |
| **cuOpt** | **Real inference** | Sub-second solve, no reason to stub |
| **Cosmos Reason** | **Real inference** | Real VLM on curated images |
| **Cosmos Transfer 2.5** | **Real inference** (pre-processed) | Weather augmentation applied at build time |
| **NeMo Guardrails** | **Real validation** | Lightweight rules engine, no GPU |
| **NV-Tesseract-AD** | **Real inference** (if included) | On simulated transformer telemetry |
| **Risk scoring** | **Real logic** | Weighted scoring with explainable breakdown |
| **ADMS capacity check** | **Narrated/displayed** | Console shows result; not a real load-flow calc |
| **Customer impact / AMI** | **Simulated** | Scenario Engine emits realistic counts from seed data |
| **Asset database** | **Synthetic** | ~100 assets on real NC geography |
| **Ground crew movements** | **Simulated** | cuOpt routes are real; crew positions are animated |
| **Fault detection** | **Scripted** | Emitted by Scenario Engine on button press |
| **Omniverse Kit substation** | **Real rendering** | Live 3D digital twin streamed via WebRTC, data-driven by Kafka |
| **Dispatcher approval** | **Real UI** | Functional approve/override controls with audit log |

---

## 13. GPU Resource Requirements

| Service | GPU | Memory | Notes |
|---------|-----|--------|-------|
| CorrDiff NIM | L40S (48GB) | ~40GB | Explicitly L40S-supported |
| Cosmos Reason 2-8B (vLLM) | L40S (48GB) | ≥32GB | 8B params FP16 + KV cache + CUDA overhead |
| cuOpt | CPU or any GPU | <4GB | Trivial for demo scale. CPU is sufficient. |
| NV-Tesseract-AD (optional) | CPU or L4 | <8GB | Lightweight anomaly detection |
| NeMo Guardrails | CPU | <1GB | Rules engine, no GPU |
| Omniverse Kit (substation DT) | RTX-class GPU | ~8-16GB | Simple scene with rasterized RTX Real-Time. L4 or RTX A4000 sufficient. 1 GPU per stream. |
| OSRM (optional) | CPU | ~2GB | Road routing |

**Minimum GPU budget: 2x L40S + 1x L4** — one L40S for CorrDiff, one L40S for Cosmos Reason (cannot coexist on 48GB), one L4 for Kit rendering. cuOpt runs on CPU.

**Comfortable GPU budget**: 2x L40S + 2x L4 (Kit on one L4, NV-Tesseract-AD on the other or expansion headroom).

---

## 14. Visual Design — Shared Style Guide

The grid console shares the visual identity established in the Industrial AI Showcase Console (`industrial-ai-showcase/console/frontend/src/showcase.css`). The style is validated and well-received — we carry it forward without coupling the implementations.

### 14.1 Design Tokens (CSS Custom Properties)

Carry forward unchanged:
```css
--showcase--color--charcoal: #151515;
--showcase--color--red: #EE0000;
--showcase--color--red-dark: #A30000;
--showcase--color--gray-medium: #6A6E73;
--showcase--color--gray-light: #F0F0F0;
--showcase--color--border: #E0E0E0;
--showcase--color--card-bg: #F3F3F3;
```

Grid-specific additions:
```css
--grid--color--risk-low: #3E8635;
--grid--color--risk-medium: #F0AB00;
--grid--color--risk-high: #EE0000;
--grid--color--risk-critical: #A30000;
--grid--color--energized: #3E8635;
--grid--color--de-energized: #6A6E73;
--grid--color--faulted: #A30000;
--grid--color--camera-active: #0066CC;
--grid--color--camera-escalated: #F0AB00;
```

### 14.2 Typography

Identical to existing showcase:
- **Headings**: `Public Sans` (400, 500, 600, 700)
- **Body/UI**: `Inter` (400, 500, 600, 700)
- **Technical/machine data**: system `monospace` (event types, trace IDs, asset IDs, solve times)
- Import: `https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap`

### 14.3 Component Patterns Carried Forward

| Pattern | Existing showcase usage | Grid console usage |
|---------|------------------------|-------------------|
| **Dark charcoal masthead** (56px, #151515) | "SHOWCASE CONSOLE" + view toggle pills | "GRID RESILIENCE OPS CENTER" + view toggle pills |
| **Pill toggle group** (9999px radius, red selected, white-on-dark unselected) | Stage / Fleet / Lineage / Architecture / Governance | Map / Dispatch / Platform / Mobile |
| **Card styling** (#F3F3F3 bg, 1px #E0E0E0 border, 4px radius, no shadow) | Event stream, metrics, camera feed | Weather panel, risk table, camera feeds, dispatch summary |
| **Event indicator dots** (8px, colored by category) | Blue/green/purple/red/orange/grey | Same palette — blue (weather), green (restoration), red (fault), orange (warning), purple (camera) |
| **Metric cards** (12px uppercase label, 16-28px bold value, optional left accent border) | Policy version, anomaly score, robot health | Forecast lead time, customers affected, ETR, solve time |
| **Monospace data display** (12px, #6A6E73) | Event kinds, Argo resource names, trace IDs | Asset IDs, camera IDs, trace IDs, cuOpt solve times |
| **Activity log / event stream** (28px row height, 16px side padding, 8px gap) | Fleet events, ops events | Grid events, camera findings, crew dispatch |

### 14.4 What's New (Grid-Specific)

These elements don't exist in the warehouse console and need new styling, but should follow the established patterns:

- **Map integration** (MapLibre GL JS) — the map replaces Isaac Sim's MJPEG viewport as the primary visual. Map controls should use the same card styling. Weather overlays should use the risk color gradient.
- **Risk heat coloring** — asset markers on the map use a 4-stop gradient: green (#3E8635) → yellow (#F0AB00) → orange → red (#A30000). Same palette as the existing status dots.
- **Customer impact banner** — new element, prominent at top. Use the existing "Look For" guidance box pattern: light background with colored left border. Yellow/orange for active outage, green for restored.
- **Dispatcher approval controls** — approve (green), modify (blue), override (orange) buttons follow the existing button variant patterns (4px radius, Inter 600, smooth hover transitions).
- **Feeder line visualization** — energized (green), de-energized (gray), faulted (red pulsing). The pulsing animation should match `showcase-argo-pulse-anim` timing (1s ease-in-out infinite).
- **Camera feed panel** — reuses the existing flush-body card pattern (`.showcase-camera-body` with padding: 0) that the warehouse console uses for its MJPEG viewport.

### 14.5 What NOT to Copy

- **Isaac Sim / MJPEG viewport** — replaced by MapLibre map
- **Purdue model diagram** — replaced by grid topology on the map
- **Lineage/pipeline DAG** — replaced by event timeline/trace view (simpler linear chain, not a node graph)
- **WebRTC streaming** — not needed (no live simulation viewport)

### 14.6 Implementation

Copy `showcase.css` as the starting point for `grid-ops.css`. Strip warehouse-specific selectors (stage view, lineage nodes, Purdue levels). Add grid-specific tokens and selectors. Same PatternFly 6 base import, same Google Fonts import, same override strategy (CSS custom properties, no preprocessor).

**PatternFly versions**: Match exactly:
```json
"@patternfly/react-core": "^6.2.0",
"@patternfly/react-icons": "^6.2.0",
"@patternfly/react-styles": "^6.2.0"
```

---

## 15. Technology Decisions (reference table)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend language | Python 3.12+ | Earth2Studio, Cosmos Reason client, Pydantic schemas — consistency |
| Backend framework | FastAPI + Uvicorn | Async, type-safe, SSE support |
| Frontend framework | React 19 + TypeScript + Vite | Industry standard, strong map ecosystem |
| UI components | PatternFly 6 | Red Hat design system |
| Map library | **MapLibre GL JS** | Open-source fork of Mapbox GL JS. No proprietary license. Self-hosted tiles via OpenMapTiles for air-gap. |
| Event streaming | **AMQ Streams** (OpenShift) / **Strimzi** (dev) | Strimzi is upstream of AMQ Streams — dev-prod parity. No Redpanda. |
| Database | **Crunchy PGO** (PostgreSQL) | Red Hat Marketplace certified. Replaces CloudNativePG. |
| Container base | **UBI9** (`registry.access.redhat.com/ubi9/python-312`) | Red Hat Universal Base Image. Freely redistributable, CVE tracking. |
| Container registry | **Red Hat Quay** | Image scanning (Clair), mirroring NIM containers |
| Event schemas | Pydantic 2.x | Type-safe, serializable, shared across services |
| Logging | structlog | Structured JSON, consistent pattern |
| Tracing | OpenTelemetry + Tempo | Red Hat build of OTel |
| Packaging | Helm (one chart per service) | Kubernetes-native, GitOps-compatible |
| GitOps | Argo CD (ApplicationSets) | Red Hat story |
| CI/CD | OpenShift Pipelines (Tekton) | Build → test → scan → sign → push → SBOM |

---

## 16. Build Sequence

### Phase A: Foundation (Week 1-2)
1. Repository scaffolding (monorepo: `services/`, `console/`, `infrastructure/`, `data/`, `docs/`)
2. Shared Python library: event schemas (Pydantic), Kafka helpers, settings, OTel setup
3. PostgreSQL schema (Crunchy PGO) + seed data script
4. Kafka topic provisioning (local Strimzi for dev)
5. Scenario Engine with REST API and basic event emission
6. OpenShift namespace + RBAC + NetworkPolicy definitions
7. Argo CD ApplicationSet structure

### Phase B: NVIDIA Integration (Week 2-4)
1. **Earth-2 pipeline**: Earth2Studio + CorrDiff NIM. Pre-stage GFS data. Validate forecast extraction.
2. **Cosmos Reason defect detection**: vLLM serving. Prompt engineering + validation harness (20+ images).
3. **cuOpt crew dispatch**: cuOpt container deployment. Validate API schema against current 26.x docs. Build VRP request assembler.
4. **Cosmos Transfer 2.5**: Weather augmentation pipeline for camera imagery. Pre-process full image set.
5. **NeMo Guardrails**: Safety validation rules for dispatch.
6. **Omniverse Kit substation**: Purchase Fab asset pack. Convert to USD. Build Kit app (from kit-app-template with `omni_default_streaming` layer). Write data-driven Kit extension (Kafka consumer → scene material updates). Verify WebRTC streaming to browser using reference code from warehouse showcase. Build private container image with purchased assets baked in.
7. **NV-Tesseract-AD** (stretch): Transformer telemetry anomaly detection.

### Phase C: Service Pipeline (Week 3-5)
1. Risk Engine: scoring algorithm with explainable breakdown, Kafka consumer/producer, REST API
2. Camera Simulator: image library (base + weather-augmented), Kafka producer, timing sync
3. Defect Detector: Kafka consumer → Cosmos Reason → findings + work orders
4. Dispatch Optimizer: cuOpt integration + NeMo Guardrails + approval state machine
5. Console Backend (BFF): route proxying, SSE multiplexer, dispatcher approval endpoints, customer impact endpoints, platform status endpoints

### Phase D: Console Frontend (Week 4-6)
1. Map view: MapLibre GL JS, asset layer, feeder lines, weather overlay
2. Customer impact banner (outage count, ETR, restoration progress)
3. Risk visualization: markers + risk table with score breakdown tooltips
4. Camera feed panel: fixed camera locations on map, cycling feed view with AI finding alert cards
5. Dispatcher Review panel: approve/modify/override controls, guardrails results, audit justification
6. Crew dispatch visualization: animated routes, dispatch summary
7. Fault/restoration: fault indicator, ADMS capacity check display, switching animation, customer restoration count
8. Event stream + timeline/lineage view
9. Platform Status tab (OCP topology, Argo CD, GPU metrics)
10. Mobile crew mockup (responsive view)
11. Scenario control bar
12. Hallway Hook variant (start at Beat 6, rewind)

### Phase E: Integration & Polish (Week 5-7)
1. End-to-end scenario validation (all beats, both variants)
2. Timing calibration for natural pacing
3. Visual polish, animations, loading states
4. Demo runbook + setup checklist
5. Pre-computed fallback data (golden forecast, dispatch, detection)
6. Observability: ServiceMonitors, Grafana dashboard, DCGM metrics
7. Geography pack structure for future expansion
8. **CC0 standard-quality substation scene**: Write USD scene generator script using `usd-core` + CC0 Poly Haven textures. Match prim hierarchy of purchased scene. Build public `kit-substation:standard` container image. Verify Kit extension works identically with both scene tiers.

### Phase F: Deployment (Week 6-8)
1. Helm charts for all services (including Kit substation)
2. Tekton pipelines: build → scan → sign → push → SBOM
3. Argo CD ApplicationSets for demo environment
4. GPU scheduling (CorrDiff + Cosmos Reason on separate L40S nodes, Kit on L4)
5. NIM container mirroring to Quay; Kit container (private) to Quay
6. SecurityContextConstraints, NetworkPolicies, sealed secrets
7. Demo environment provisioning runbook

---

## 17. Risk Analysis and Mitigations

### Risk 1: Cosmos Reason fails to reliably detect defects

**Mitigation**: Build validation harness early. Test 20+ candidate images with varied prompts. If VLM reliability is insufficient, use a hybrid approach: fine-tuned YOLO for detection + Cosmos Reason for description only. Both models doing real inference — technically honest.

### Risk 2: CorrDiff NIM warm-up latency disrupts demo

**Mitigation**: Warm up before demo (3 inference passes). Pre-computed fallback ready. Loading animation in console.

### Risk 3: cuOpt unavailable or API schema changed

**Mitigation**: Validate API schema against current 26.x docs in Phase B. Include OR-Tools as backup solver. Pre-computed golden dispatch result as emergency fallback.

### Risk 4: Map tile loading fails offline

**Mitigation**: Self-hosted vector tiles via OpenMapTiles cached for Piedmont NC corridor (zoom 8-16). MapLibre supports offline tile sources natively.

### Risk 5: Geographic realism — seeded assets look fake

**Mitigation**: Place assets along real road corridors using OSM data. Realistic inter-pole spacing (100-150m). Radial feeder topology with tie points. Reference publicly available utility service territory maps for plausible corridor selection.

### Risk 6: NGC API key / NIM container access

**Mitigation**: Pre-pull all NIM containers. Mirror to Quay. Document provisioning in runbook.

---

## 18. Stretch Goals

### S1: Geography Pack — California Wildfire (PSPS)
Same service architecture, different scenario YAML:
- Seed data: ~100 assets in southern California mountain terrain
- Weather threat: Santa Ana winds (high wind, low humidity, Red Flag warning)
- Risk scoring: wildfire ignition probability (fire weather index, fuel moisture, vegetation proximity)
- Response: PSPS (Public Safety Power Shutoff) de-energization decision
- Customer impact: selective de-energization minimizing customer impact

### S2: OPAI Consortium LLM Integration (Forward-Looking)
When the EPRI/NVIDIA Open Power AI Consortium releases its energy-domain LLM as a NIM, integrate as a "copilot" layer providing natural language summaries of risk scores, dispatch decisions, and storm response actions. Accessible via a chat sidebar in the console.

---

## 19. Verification Plan

### Unit Tests
- Risk scoring: weights, edge cases, explainable breakdowns
- cuOpt request assembly: validate JSON against actual 26.x API
- Cosmos Reason response parsing: region extraction, empty findings, malformed responses
- NeMo Guardrails: safety rule validation (fault zone, certification, shift time)
- Customer impact calculation: segment → customer count aggregation

### Integration Tests
- Weather Service → Kafka → Risk Engine: forecast → risk scores
- Camera Simulator → Kafka → Defect Detector → Kafka: camera frames → findings
- Work Orders → NeMo Guardrails → cuOpt → Dispatch (pending) → Approval → Dispatch (approved)
- Fault → AMI outages → customer impact → re-optimization
- Console Backend SSE: all event types stream correctly

### Cosmos Reason Validation Harness
- Run each curated image (base + weather-augmented) through detection prompt
- Gate: >90% accuracy on curated set before integration
- Document prompt version that achieves threshold

### Demo Dry Run Checklist
- [ ] All NIM containers pulled and running (CorrDiff, vLLM, cuOpt, Kit substation)
- [ ] CorrDiff NIM warmed up (3 inference passes)
- [ ] PostgreSQL seeded with asset data (including customers_per_segment)
- [ ] Kafka topics created (KafkaTopic CRs applied)
- [ ] Map tiles cached for Piedmont NC corridor (zoom 8-16)
- [ ] Camera images loaded (base + Cosmos Transfer augmented)
- [ ] cuOpt health check passing, API schema validated
- [ ] NeMo Guardrails rules loaded
- [ ] Console frontend building and serving
- [ ] Full scenario run-through (both Hallway Hook and Full Demo)
- [ ] Fallback data pre-computed and accessible
- [ ] Argo CD showing all apps synced (for Platform Status tab)
- [ ] Kit substation streaming to console via WebRTC (3D panel rendering)
- [ ] Kit extension receiving Kafka events and updating scene materials
- [ ] DCGM Exporter metrics flowing to Prometheus (for GPU utilization chart)
