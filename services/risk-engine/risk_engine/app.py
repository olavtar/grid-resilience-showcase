# This project was developed with assistance from AI tools.

"""Risk Engine — FastAPI application for asset risk scoring."""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException

from grid_common.events import AssetRiskScore
from grid_common.kafka import create_producer
from grid_common.logging import setup_logging
from risk_engine.consumer import consumer_loop
from risk_engine.settings import RiskEngineSettings

logger = structlog.get_logger()
settings = RiskEngineSettings()
producer = None
risk_scores: dict[str, AssetRiskScore] = {}
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global producer
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    producer = create_producer(settings)

    thread = threading.Thread(
        target=consumer_loop,
        args=(settings, producer, risk_scores, lock),
        daemon=True,
    )
    thread.start()
    logger.info("risk_engine_started")
    yield
    if producer:
        producer.flush()
    logger.info("risk_engine_stopped")


app = FastAPI(title="Risk Engine", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if producer is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    return {"status": "ready"}


@app.get("/assets/ranked")
async def assets_ranked(limit: int = 20, min_score: float = 0.0) -> list[dict[str, Any]]:
    """Return assets ranked by composite risk score."""
    with lock:
        scores = list(risk_scores.values())
    filtered = [s for s in scores if s.composite_score >= min_score]
    filtered.sort(key=lambda s: s.composite_score, reverse=True)
    return [s.model_dump() for s in filtered[:limit]]


@app.get("/assets/{asset_id}/risk")
async def asset_risk(asset_id: str) -> dict[str, Any]:
    """Return the current risk score for a specific asset."""
    with lock:
        score = risk_scores.get(asset_id)
    if score is None:
        raise HTTPException(status_code=404, detail=f"No risk score for {asset_id}")
    return score.model_dump()
