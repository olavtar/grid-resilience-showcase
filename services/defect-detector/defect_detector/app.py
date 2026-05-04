# This project was developed with assistance from AI tools.

"""Defect Detector — FastAPI application for Cosmos Reason defect detection."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException

from defect_detector.consumer import consumer_loop
from defect_detector.settings import DefectDetectorSettings
from grid_common.events import InspectionFinding
from grid_common.kafka import create_producer
from grid_common.logging import setup_logging

logger = structlog.get_logger()
settings = DefectDetectorSettings()
producer = None
findings_buffer: deque[InspectionFinding] = deque(maxlen=200)
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global producer
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    producer = create_producer(settings)

    def _safe_consumer() -> None:
        try:
            consumer_loop(settings, producer, findings_buffer, lock)
        except Exception:
            logger.exception("consumer_thread_crashed")

    thread = threading.Thread(
        target=_safe_consumer,
        daemon=True,
    )
    thread.start()
    logger.info("defect_detector_started", vllm_url=settings.vllm_base_url)
    yield
    if producer:
        producer.flush()
    logger.info("defect_detector_stopped")


app = FastAPI(title="Defect Detector", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if producer is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{settings.vllm_base_url}/health", timeout=5.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=503, detail="vLLM not ready")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"vLLM unreachable: {e}") from None
    return {"status": "ready"}


@app.get("/findings/recent")
async def findings_recent(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent findings from the ring buffer."""
    with lock:
        items = list(findings_buffer)
    items.reverse()
    return [f.model_dump() for f in items[:limit]]


@app.get("/findings/{camera_id}")
async def findings_by_camera(camera_id: str) -> list[dict[str, Any]]:
    """Return findings for a specific camera."""
    with lock:
        items = [f for f in findings_buffer if f.camera_id == camera_id]
    items.reverse()
    return [f.model_dump() for f in items]
