# Grid Resilience Operations Center

An energy-vertical demo showcasing NVIDIA's AI stack running on Red Hat OpenShift. The demo simulates an ice storm scenario on a distribution corridor, demonstrating AI-powered weather forecasting, automated defect detection, GPU-optimized crew dispatch, and a real-time 3D substation digital twin.

> [!NOTE]
> This project was developed with assistance from AI tools.

## What It Does

A scripted demo walks through storm preparedness and response for an electric utility operations center:

- **Weather forecasting** with NVIDIA Earth-2 CorrDiff for hyperlocal 3km downscaling
- **Camera-based defect detection** with Cosmos Reason for AI observation of fixed infrastructure cameras
- **Crew dispatch optimization** with cuOpt for GPU-accelerated vehicle routing
- **3D substation digital twin** with Omniverse Kit streaming via WebRTC
- **Risk scoring** across weather exposure, asset age, vegetation proximity, and inspection recency

The console provides a map view with weather overlays, asset risk rankings, camera findings, crew route visualization, and customer impact tracking through each phase of the scenario.

## Cluster Prerequisites

- OpenShift 4.x cluster
- NVIDIA GPU Operator installed
- 3x L40S GPU nodes (CorrDiff, Cosmos Reason via vLLM, Omniverse Kit)
- 1x L4 GPU node (cuOpt)
- AMQ Streams or Strimzi Kafka operator
- Crunchy PGO (PostgreSQL operator)
- Argo CD for GitOps deployment

## Running

### Scale up

```bash
oc scale deployment/corrdiff-nim deployment/vllm-cosmos deployment/cuopt deployment/kit-substation deployment/coturn -n grid-ops-ai --replicas=1
oc scale deployment/weather-service deployment/scenario-engine deployment/camera-simulator deployment/defect-detector deployment/dispatch-optimizer deployment/risk-engine -n grid-ops-services --replicas=1
oc scale deployment/console-backend deployment/console-frontend -n grid-ops-console --replicas=1
```

### Scale down

```bash
oc scale deployment/corrdiff-nim deployment/vllm-cosmos deployment/cuopt deployment/kit-substation deployment/coturn -n grid-ops-ai --replicas=0
oc scale deployment/weather-service deployment/scenario-engine deployment/camera-simulator deployment/defect-detector deployment/dispatch-optimizer deployment/risk-engine -n grid-ops-services --replicas=0
oc scale deployment/console-backend deployment/console-frontend -n grid-ops-console --replicas=0
```

### Seed the database

```bash
oc port-forward -n grid-ops-infra pod/<postgres-pod> 5432:5432 &
python3 data/seed/load_seed_data.py "postgresql://gridops:<password>@localhost:5432/gridops?sslmode=require"
```

### Seed the CorrDiff cache

After the weather-service and CorrDiff NIM are running:

```bash
oc port-forward -n grid-ops-services svc/weather-service 8180:8080 &
curl -X POST http://localhost:8180/forecast/run
```

This runs a live CorrDiff inference (~45s) and caches the result. Subsequent scenario starts use the cache for instant replay.

### Access the console

The console is exposed via an OpenShift Route:

```bash
oc get route console-frontend -n grid-ops-console -o jsonpath='{.spec.host}'
```
