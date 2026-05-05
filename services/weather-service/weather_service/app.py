# This project was developed with assistance from AI tools.

"""Weather Service — FastAPI application wrapping Earth-2 CorrDiff NIM."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException

from grid_common.events import WeatherForecast
from grid_common.kafka import create_producer
from grid_common.logging import setup_logging
from weather_service.forecast import publish_cached_forecast, run_forecast, warmup_nim
from weather_service.settings import WeatherServiceSettings

logger = structlog.get_logger()
settings = WeatherServiceSettings()
producer = None
http_client: httpx.AsyncClient | None = None
latest_forecasts: list[WeatherForecast] = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global producer, http_client
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    producer = create_producer(settings)
    http_client = httpx.AsyncClient(timeout=60.0)
    logger.info("weather_service_started", corrdiff_url=settings.corrdiff_nim_url)
    yield
    if http_client:
        await http_client.aclose()
    if producer:
        producer.flush()
    logger.info("weather_service_stopped")


app = FastAPI(title="Weather Service", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if producer is None or http_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    try:
        resp = await http_client.get(f"{settings.corrdiff_nim_url}/v1/health/ready", timeout=5.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=503, detail="CorrDiff NIM not ready")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"CorrDiff NIM unreachable: {e}") from None
    return {"status": "ready"}


@app.get("/forecast/current")
async def forecast_current() -> dict[str, Any]:
    """Return the latest forecast from in-memory cache."""
    if not latest_forecasts:
        raise HTTPException(status_code=404, detail="No forecast available yet")
    return {
        "forecast_count": len(latest_forecasts),
        "forecasts": [f.model_dump() for f in latest_forecasts],
    }


@app.post("/forecast/run")
async def forecast_run() -> dict[str, Any]:
    """Trigger CorrDiff NIM inference and publish results to Kafka."""
    global latest_forecasts
    if producer is None or http_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    forecasts = await run_forecast(settings, producer, http_client)
    latest_forecasts = forecasts

    return {
        "status": "published",
        "forecast_hours": [f.forecast_hour for f in forecasts],
        "grid_cells": sum(len(f.grid_cells) for f in forecasts),
    }


@app.post("/forecast/publish-cached")
async def forecast_publish_cached() -> dict[str, Any]:
    """Republish the last CorrDiff forecast from cached output (instant)."""
    global latest_forecasts
    if producer is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    forecasts = publish_cached_forecast(settings, producer)
    if forecasts is None:
        raise HTTPException(status_code=404, detail="No cached forecast available")

    latest_forecasts = forecasts
    return {
        "status": "published",
        "source": "cached",
        "forecast_hours": [f.forecast_hour for f in forecasts],
        "grid_cells": sum(len(f.grid_cells) for f in forecasts),
    }


@app.post("/forecast/warmup")
async def forecast_warmup() -> dict[str, Any]:
    """Warm up CorrDiff NIM with throwaway inference passes."""
    if http_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    success = await warmup_nim(settings, http_client)
    return {"status": "ok" if success else "failed"}
