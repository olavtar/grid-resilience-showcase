# This project was developed with assistance from AI tools.

"""Scenario Engine — FastAPI application for scripted demo orchestration."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import structlog
import yaml
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from grid_common.events import OpsEvent, Severity
from grid_common.kafka import create_producer, publish_event
from grid_common.logging import setup_logging
from scenario_engine.emitter import (
    emit_escalate_events,
    emit_fault_events,
    emit_forecast_events,
    emit_storm_events,
)
from scenario_engine.settings import ScenarioEngineSettings
from scenario_engine.state import Beat, ScenarioState

logger = structlog.get_logger()
settings = ScenarioEngineSettings()
state = ScenarioState()
producer: Producer | None = None
http_client: httpx.AsyncClient | None = None


def _producer() -> Producer:
    assert producer is not None
    return producer


def _client() -> httpx.AsyncClient:
    assert http_client is not None
    return http_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global producer, http_client
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    producer = create_producer(settings)
    http_client = httpx.AsyncClient(timeout=300.0)
    logger.info("scenario_engine_started", scenario_dir=settings.scenario_dir)
    yield
    if http_client:
        await http_client.aclose()
    if producer:
        producer.flush()
    logger.info("scenario_engine_stopped")


app = FastAPI(title="Scenario Engine", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ScenarioInfo(BaseModel):
    id: str
    name: str
    description: str
    geography: str


class StateResponse(BaseModel):
    scenario_id: str | None
    scenario_name: str | None
    current_beat: str
    is_running: bool
    storm_triggered: bool
    fault_triggered: bool
    events_emitted: int


class ActionResponse(BaseModel):
    action: str
    beat: str
    events_emitted: int
    message: str


# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------


def _load_scenarios() -> list[dict[str, Any]]:
    """Load scenario definitions from YAML files."""
    scenario_dir = Path(settings.scenario_dir)
    scenarios = []
    if scenario_dir.exists():
        for f in sorted(scenario_dir.glob("*.yaml")):
            with open(f) as fh:
                data = yaml.safe_load(fh)
                if data:
                    data["_file"] = f.name
                    scenarios.append(data)
    if not scenarios:
        scenarios.append(
            {
                "id": "ice_storm_piedmont",
                "name": "Ice Storm — Piedmont NC",
                "description": (
                    "18-hour ice storm scenario on the Piedmont NC distribution corridor."
                ),
                "geography": "piedmont_nc",
                "lat_min": 36.05,
                "lat_max": 36.12,
                "lon_min": -79.55,
                "lon_max": -79.40,
                "escalate_cameras": [
                    "CAM-P037",
                    "CAM-P052",
                    "CAM-P063",
                    "CAM-SUB-A",
                    "CAM-P041",
                ],
                "fault": {
                    "feeder_id": "F-12",
                    "segment_id": "SEG-052",
                    "affected_customers": 847,
                    "lat": 36.088,
                    "lon": -79.465,
                    "switch_id": "TS-04",
                    "customers_restored": 312,
                    "ami_meters": 20,
                },
            }
        )
    return scenarios


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if producer is None:
        raise HTTPException(status_code=503, detail="Producer not initialized")
    return {"status": "ready"}


@app.get("/scenarios", response_model=list[ScenarioInfo])
async def list_scenarios() -> list[ScenarioInfo]:
    scenarios = _load_scenarios()
    return [
        ScenarioInfo(
            id=s.get("id", "unknown"),
            name=s.get("name", "Unnamed"),
            description=s.get("description", ""),
            geography=s.get("geography", ""),
        )
        for s in scenarios
    ]


@app.get("/scenario/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    return StateResponse(
        scenario_id=state.scenario_id,
        scenario_name=state.scenario_name,
        current_beat=state.current_beat.value,
        is_running=state.is_running,
        storm_triggered=state.storm_triggered,
        fault_triggered=state.fault_triggered,
        events_emitted=state.events_emitted,
    )


@app.post("/scenario/start", response_model=ActionResponse)
async def start_scenario(scenario_id: str = "ice_storm_piedmont") -> ActionResponse:
    if state.is_running:
        raise HTTPException(status_code=409, detail="Scenario already running. Reset first.")

    scenarios = _load_scenarios()
    config = next((s for s in scenarios if s.get("id") == scenario_id), None)
    if not config:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    state.reset()
    state.scenario_id = scenario_id
    state.scenario_name = config.get("name", scenario_id)
    state.scenario_config = config
    state.is_running = True

    trace_id = str(uuid.uuid4()).replace("-", "")
    beat = state.advance()

    try:
        resp = await _client().post(f"{settings.weather_service_url}/forecast/run")
        if resp.status_code == 200:
            logger.info("weather_service_forecast_triggered")
            count = 1
        else:
            logger.warning("weather_service_failed", status=resp.status_code)
            count = emit_forecast_events(_producer(), config, trace_id)
    except Exception:
        logger.warning("weather_service_unreachable_using_fallback")
        count = emit_forecast_events(_producer(), config, trace_id)

    state.events_emitted += count

    logger.info("scenario_started", scenario_id=scenario_id, beat=beat.value)

    return ActionResponse(
        action="start",
        beat=beat.value,
        events_emitted=state.events_emitted,
        message=f"Scenario '{state.scenario_name}' started at beat: {beat.value}",
    )


@app.post("/scenario/advance", response_model=ActionResponse)
async def advance_scenario() -> ActionResponse:
    if not state.is_running:
        raise HTTPException(status_code=409, detail="No scenario running.")

    trace_id = str(uuid.uuid4()).replace("-", "")
    beat = state.advance()
    config = state.scenario_config
    count = 0

    if beat == Beat.ESCALATE:
        count = emit_escalate_events(_producer(), config, trace_id)
    elif beat in (Beat.TRIAGE, Beat.DETECT, Beat.DISPATCH, Beat.TRACE):
        ops = OpsEvent(
            category="system",
            title=f"Beat advanced: {beat.value}",
            detail=f"Scenario progressed to {beat.value} phase.",
            severity=Severity.INFO,
            trace_id=trace_id,
            source_service="scenario-engine",
        )
        p = _producer()
        publish_event(p, "grid.ops.events", ops)
        p.flush()
        count = 1

    state.events_emitted += count
    logger.info("scenario_advanced", beat=beat.value, events=count)

    return ActionResponse(
        action="advance",
        beat=beat.value,
        events_emitted=state.events_emitted,
        message=f"Advanced to beat: {beat.value}",
    )


@app.post("/scenario/trigger-storm", response_model=ActionResponse)
async def trigger_storm() -> ActionResponse:
    if not state.is_running:
        raise HTTPException(status_code=409, detail="No scenario running.")
    if state.storm_triggered:
        raise HTTPException(status_code=409, detail="Storm already triggered.")

    trace_id = str(uuid.uuid4()).replace("-", "")
    state.current_beat = Beat.STORM
    count = emit_storm_events(_producer(), state.scenario_config, trace_id)
    state.storm_triggered = True
    state.events_emitted += count

    logger.info("storm_triggered", events=count)

    return ActionResponse(
        action="trigger-storm",
        beat=Beat.STORM.value,
        events_emitted=state.events_emitted,
        message="Storm conditions activated.",
    )


@app.post("/scenario/trigger-fault", response_model=ActionResponse)
async def trigger_fault() -> ActionResponse:
    if not state.is_running:
        raise HTTPException(status_code=409, detail="No scenario running.")
    if state.fault_triggered:
        raise HTTPException(status_code=409, detail="Fault already triggered.")

    trace_id = str(uuid.uuid4()).replace("-", "")
    count = emit_fault_events(_producer(), state.scenario_config, trace_id)
    state.fault_triggered = True
    state.events_emitted += count

    logger.info("fault_triggered", events=count)

    return ActionResponse(
        action="trigger-fault",
        beat=Beat.STORM.value,
        events_emitted=state.events_emitted,
        message="Fault triggered with AMI outages and restoration switching.",
    )


@app.post("/scenario/reset", response_model=ActionResponse)
async def reset_scenario() -> ActionResponse:
    state.reset()
    logger.info("scenario_reset")
    return ActionResponse(
        action="reset",
        beat=Beat.IDLE.value,
        events_emitted=0,
        message="Scenario reset to idle.",
    )
