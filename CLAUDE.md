# Claude Code project conventions

This file is read automatically at the start of any Claude Code session in this repository. It is the persistent context that keeps work coherent across sessions.

## Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

    State your assumptions explicitly. If uncertain, ask.
    If multiple interpretations exist, present them - don't pick silently.
    If a simpler approach exists, say so. Push back when warranted.
    If something is unclear, stop. Name what's confusing. Ask.

## Simplicity First

Minimum code that solves the problem. Nothing speculative.

    No features beyond what was asked.
    No abstractions for single-use code.
    No "flexibility" or "configurability" that wasn't requested.
    No error handling for impossible scenarios.
    If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

    Don't "improve" adjacent code, comments, or formatting.
    Don't refactor things that aren't broken.
    Match existing style, even if you'd do it differently.
    If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

    Remove imports/variables/functions that YOUR changes made unused.
    Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

    "Add validation" → "Write tests for invalid inputs, then make them pass"
    "Fix the bug" → "Write a test that reproduces it, then make it pass"
    "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Project mission

Build a Grid Resilience Operations Center — a standalone energy-vertical demo showcasing NVIDIA's AI stack (Earth-2, cuOpt, Cosmos Reason, Cosmos Transfer, Omniverse Kit, NeMo Guardrails) running on Red Hat OpenShift. The demo targets electric utility customers and shows AI-powered storm preparedness, defect detection via fixed cameras, GPU-accelerated crew dispatch optimization, and a real-time 3D substation digital twin.

This is a **standalone project** — not an extension of the warehouse showcase at `industrial-ai-showcase/`. Different NVIDIA products, different domain, different console design. They share visual styling (PatternFly 6, same design tokens) but no code dependencies.

## The plan

The implementation plan is at `docs/plan.md`. It is the authoritative source for architecture, service specifications, data models, demo narrative, build sequence, and technology decisions. Read it before writing code. When the plan and this file disagree, this file wins on conventions; the plan wins on architecture and scope.

A stakeholder review consolidation is at `docs/review-consolidation.md` for context on design decisions and addressed feedback.

## Hard constraints

1. **Deployment target is OpenShift.** Use OpenShift primitives (Routes, SCCs, Projects, Operators) where appropriate. OperatorHub is the default installation method for anything with an operator.
2. **GitOps-first.** Nothing is `oc apply`'d by hand into long-lived state. Argo CD reconciles from this repo.
3. **Air-gapped must remain possible.** Every external dependency (container image, chart, model weight) must be mirrorable. Don't introduce components that require live internet at runtime without documenting an offline path.
4. **GPU budget: 2x L40S + 1x L4 minimum.** One L40S for CorrDiff NIM (~40GB), one L40S for Cosmos Reason via vLLM (>=32GB). They cannot coexist on a single 48GB L40S. Kit rendering on L4. cuOpt on CPU. GPU class targeting uses native GFD labels (`nvidia.com/gpu.product`), not custom labels.
5. **No specific company names in demo narrative.** Narrator scripts, closing notes, and any customer-facing text must use role-based language ("utilities", "your GIS", "your work management system"), never "Duke Energy", "Esri ArcGIS", "IBM Maximo", etc. Internal documentation (plan, architecture) may reference specific products for engineering context.
6. **No unsubstantiated performance claims.** Don't claim "tested at X scale" unless it has been tested. Use directional language ("designed for", "GPU-accelerated for large-scale use") instead.
7. **Cosmos Reason is an observation model.** It observes images and answers questions about what it sees. It produces natural language descriptions and classifications. It does NOT produce visual annotations, bounding boxes, region highlights, or image overlays. Display findings as text alert cards beside camera feeds.
8. **Dual-quality 3D scene strategy.** The Omniverse Kit substation has two scene tiers: `high` (purchased Fab asset, private Quay container) and `standard` (CC0 code-generated primitives, public). Both share the same prim hierarchy so the Kit extension works identically. Development uses the `high` scene. The `standard` fallback is built toward the end of the project (Phase E). Purchased assets are NEVER committed to the repo — they live in `.gitignore`'d directories and are baked into private container images.
9. **Fixed cameras, not drones.** Inspection is via existing pole-mounted and substation security cameras with AI-escalated monitoring frequency. Crews are dispatched to repair, not inspect. No BVLOS, no autonomous drones, no FAA considerations.
10. **Human-in-the-loop for crew dispatch.** AI recommends, dispatcher approves. The demo shows a Dispatcher Review panel with approve/modify/override controls and audit justification. Storm mode enables auto-approval for critical work orders, but the capability to override is always visible.
11. **Red Hat must be visible in the demo.** The narrator mentions OpenShift, GPU Operator, Edge Manager, and GitOps at specific points in the script. The console has a Platform Status view showing OpenShift topology, Argo CD sync, and GPU metrics. This is not "NVIDIA on Linux" — it is a Red Hat showcase.
12. **Edge story uses RHEL + Edge Manager**, not MicroShift. Edge devices (Jetson Orin at substations) run RHEL managed by Red Hat Edge Manager for OS provisioning, model updates, and device lifecycle.

## Technology decisions (locked)

| Decision | Choice | Notes |
|----------|--------|-------|
| Backend language | Python 3.12+ | All services. Earth2Studio, Pydantic, confluent-kafka. |
| Backend framework | FastAPI + Uvicorn | Async, type-safe, SSE support. |
| Frontend | React 19 + TypeScript + Vite | |
| UI components | PatternFly 6 | Match existing showcase styling — see `docs/plan.md` Section 14. |
| Map library | MapLibre GL JS | Open-source. Self-hosted tiles via OpenMapTiles for air-gap. |
| Event streaming | AMQ Streams (OpenShift) / Strimzi (dev) | No Redpanda. Strimzi is upstream of AMQ Streams. |
| Database | Crunchy PGO (PostgreSQL) | Red Hat Marketplace certified. |
| Container base | UBI9 (`registry.access.redhat.com/ubi9/python-312`) | All custom services. |
| Container registry | Red Hat Quay | Image scanning (Clair), NIM mirroring. |
| Logging | structlog | JSON to stdout. |
| Tracing | OpenTelemetry + Tempo | Red Hat build of OTel. Trace IDs propagated through Kafka headers. |
| Packaging | Helm (one chart per service) | No umbrella charts. |
| GitOps | Argo CD (ApplicationSets) | Sync waves for ordering. |
| CI/CD | OpenShift Pipelines (Tekton) | Build, scan, sign (cosign), push, SBOM (Syft). |
| Kit streaming | WebRTC via `@nvidia/omniverse-webrtc-streaming-library` | Reference code from `industrial-ai-showcase` console. |

## NVIDIA products in the demo

| Product | Role | Serving |
|---------|------|---------|
| Earth-2 CorrDiff NIM | 3km weather downscaling | `nvcr.io/nim/nvidia/corrdiff:1.1.0` on L40S |
| Cosmos Reason 2-8B | Camera frame observation + defect classification | vLLM (`nvidia/Cosmos-Reason2-8B`) on L40S |
| cuOpt | Crew dispatch optimization (VRP) | `nvidia/cuopt:26.06-cuda12.9-py3.13` on CPU. Apache 2.0. |
| Cosmos Transfer 2.5 | Weather augmentation of camera imagery | Build-time preprocessing, not runtime. |
| Omniverse Kit | 3D substation digital twin rendering | Kit App Streaming (WebRTC) on L4. |
| NeMo Guardrails | Safety validation for dispatch | Lightweight, CPU, Apache 2.0. |
| NV-Tesseract-AD | Transformer anomaly detection (stretch) | NIM on CPU or L4. |

## Coding conventions

- **Python**: Type hints required. `ruff` + `mypy` in CI. Python 3.12+.
- **TypeScript**: Vite + React. PatternFly for UI consistency.
- **Helm**: One chart per component. Chart values preferred over Kustomize overlays.
- **YAML**: Stable field order. Use `yq` in scripts.
- **Shell**: `bash` with `set -euo pipefail`. Anything over ~50 lines → Python.
- **Dependencies**: Pin with upper bounds (e.g., `fastapi>=0.115.0,<1.0`).
- **Docstrings**: One-line only. No `Args:`/`Returns:`/`Raises:` sections.
- **Comments**: Concise. No company names, no individual names, no internal project references.
- **Tests**: One-line docstrings describing what the test verifies. Bind mock servers to `127.0.0.1`.

## Git conventions

- Trunk: `main`.
- Every change is a PR with Conventional Commits title (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
- Signed commits (DCO sign-off minimum).
- Container images Sigstore-signed in CI. SBOMs generated per image (Syft, SPDX JSON).

## Shared visual identity

This project shares the design language from `industrial-ai-showcase/console/frontend/src/showcase.css`. Key tokens:

```css
--showcase--color--charcoal: #151515;    /* masthead, dark elements */
--showcase--color--red: #EE0000;         /* primary accent, Red Hat red */
--showcase--color--red-dark: #A30000;    /* danger states */
--showcase--color--gray-medium: #6A6E73; /* secondary text */
--showcase--color--gray-light: #F0F0F0;  /* hover states */
--showcase--color--border: #E0E0E0;      /* card/divider borders */
--showcase--color--card-bg: #F3F3F3;     /* card backgrounds */
```

Fonts: `Public Sans` (headings), `Inter` (body/UI), system `monospace` (technical data).
Pattern: Dark charcoal masthead (56px), pill toggle for views, flat cards with 1px borders, 8px colored indicator dots for event categories.

Fork `showcase.css` as the starting point for this project's styles. Strip warehouse-specific selectors. Add grid-specific tokens for risk colors, energized/faulted states, and camera status.

## Before you start writing code

1. Read `docs/plan.md` — at minimum the build sequence (Section 16) and the service specifications (Section 8) for whatever you're building.
2. Check the technology decisions table above. Don't introduce alternatives without asking.
3. Respect the GPU budget. Check Section 13 of the plan before adding GPU workloads.
4. If you're writing narrator-facing text, use role-based language. No company names.
5. If you're working on the Omniverse Kit substation, remember: development uses the `high` quality purchased scene. The `standard` CC0 fallback comes later (Phase E).

## Escalation gates — stop and ask a human

- Contradiction with a locked technology decision
- New external dependency not in the plan
- Scope expansion beyond the plan's build sequence
- Air-gap compromise (component requires live internet with no offline path)
- GPU workload that doesn't fit the 2x L40S + 1x L4 budget
- Any work on the CC0 standard-quality scene before Phase E
