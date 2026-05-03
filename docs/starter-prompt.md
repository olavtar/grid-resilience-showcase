# Starter Prompt for Claude Code

Copy and paste the following prompt into Claude Code when opening this project for the first time.

---

Read CLAUDE.md and docs/plan.md thoroughly — these define the project architecture, constraints, and build sequence. This is a greenfield project: the Grid Resilience Operations Center, a Red Hat + NVIDIA energy-vertical demo.

Start with Phase A (Foundation) from the build sequence in docs/plan.md Section 16:

1. Set up the monorepo structure: `services/`, `console/`, `infrastructure/`, `data/`, `docs/` directories
2. Create the shared Python library at `services/common/grid_common/` with:
   - `events.py` — all Pydantic event schemas from Section 8 of the plan (WeatherForecast, WeatherAlert, AssetRiskScore, InspectionFrame, InspectionFinding, WorkOrder, DispatchAssignment, FaultEvent, RestorationEvent, CrewTelemetry, OpsEvent, CustomerImpact)
   - `kafka.py` — Kafka producer/consumer helpers using confluent-kafka
   - `settings.py` — shared Pydantic settings base pattern
   - `tracing.py` — OpenTelemetry setup with Kafka header trace propagation
   - `logging.py` — structlog JSON configuration
3. Create `pyproject.toml` at the repo root with ruff + mypy configuration, Python 3.12+ target
4. Create the PostgreSQL schema from Section 9.1 of the plan (assets, feeders, segments, switches, cameras, crews tables) as a SQL migration file at `data/seed/schema.sql`
5. Create the seed data JSON files at `data/seed/` — realistic assets placed along road corridors in the Piedmont NC region per the plan's specification
6. Create a `docker-compose.yml` for local dev with Strimzi Kafka and PostgreSQL
7. Scaffold the Scenario Engine service at `services/scenario-engine/` with FastAPI endpoints from Section 8.6 of the plan

Follow CLAUDE.md for all coding conventions, dependency pinning, and container base image choices. The plan has the complete specifications — use it as the source of truth for schemas, endpoints, and service interfaces.
