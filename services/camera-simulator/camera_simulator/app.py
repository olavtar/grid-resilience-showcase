# This project was developed with assistance from AI tools.

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import structlog
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException

from camera_simulator.publisher import handle_escalate_event, publish_frame
from camera_simulator.settings import CameraSimulatorSettings
from grid_common.kafka import consume_events, create_consumer, create_producer
from grid_common.logging import setup_logging

logger = structlog.get_logger()
settings = CameraSimulatorSettings()
producer: Producer | None = None


def _producer() -> Producer:
    """Return the producer, asserting it has been initialized."""
    assert producer is not None
    return producer


@dataclass
class CameraState:
    """Runtime state for a single camera."""

    camera_id: str
    asset_id: str
    image_path: str
    mode: str = "baseline"
    baseline_interval: int = 3600
    escalated_interval: int = 30
    current_interval: int = 3600
    last_published: float = -1.0
    frame_sequence: int = 0


camera_states: dict[str, CameraState] = {}
_publisher_task: asyncio.Task[None] | None = None
_consumer_thread: threading.Thread | None = None
_shutdown_event = threading.Event()


CAMERA_IMAGES: dict[str, list[str]] = {
    "CAM-P037": ["cam_p037_cracked.jpg"],
    "CAM-P052": ["cam_p052_veg1.jpg"],
    "CAM-P063": ["cam_p063_ice.jpg"],
}


def _image_for_camera(camera_id: str, sequence: int) -> str:
    """Select an image file for a camera based on frame sequence."""
    images = CAMERA_IMAGES.get(camera_id, ["placeholder.png"])
    idx = min(sequence, len(images) - 1)
    return str(Path(settings.image_dir) / "base" / images[idx])


def _load_cameras_from_db() -> dict[str, CameraState]:
    """Load camera definitions from the cameras table."""
    states: dict[str, CameraState] = {}
    try:
        with psycopg.connect(settings.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, asset_id, baseline_interval_seconds, "
                    "escalated_interval_seconds FROM cameras WHERE status = 'active'"
                )
                for row in cur.fetchall():
                    cam_id, asset_id, baseline, escalated = row
                    states[cam_id] = CameraState(
                        camera_id=cam_id,
                        asset_id=asset_id or "",
                        image_path=_image_for_camera(cam_id, 0),
                        baseline_interval=baseline or 3600,
                        escalated_interval=escalated or 30,
                        current_interval=baseline or 3600,
                        last_published=time.time(),
                    )
        logger.info("cameras_loaded", count=len(states))
    except Exception:
        logger.warning("cameras_db_unavailable", msg="starting with no cameras")
    return states


async def _frame_publisher_loop() -> None:
    """Periodically check cameras and publish frames when interval has elapsed."""
    while True:
        now = time.time()
        for state in camera_states.values():
            if state.camera_id not in CAMERA_IMAGES:
                continue
            elapsed = now - state.last_published
            if elapsed >= state.current_interval:
                state.frame_sequence += 1
                publish_frame(
                    _producer(),
                    camera_id=state.camera_id,
                    asset_id=state.asset_id,
                    image_path=_image_for_camera(state.camera_id, state.frame_sequence),
                    frame_sequence=state.frame_sequence,
                    escalated=state.mode == "escalated",
                )
                state.last_published = now
        await asyncio.sleep(5)


def _escalation_consumer_loop() -> None:
    """Daemon thread: consume CameraEscalate events from Kafka."""
    consumer = create_consumer(
        settings,
        group_id=settings.kafka_consumer_group_id,
        topics=["grid.cameras.escalate"],
    )
    try:
        while not _shutdown_event.is_set():
            messages = consume_events(consumer, timeout=1.0)
            for msg in messages:
                handle_escalate_event(msg, camera_states)
    finally:
        consumer.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global producer, _publisher_task, _consumer_thread
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    producer = create_producer(settings)

    camera_states.update(_load_cameras_from_db())

    _publisher_task = asyncio.create_task(_frame_publisher_loop())

    _shutdown_event.clear()
    _consumer_thread = threading.Thread(
        target=_escalation_consumer_loop, daemon=True, name="escalation-consumer"
    )
    _consumer_thread.start()

    logger.info("camera_simulator_started", cameras=len(camera_states))
    yield

    _shutdown_event.set()
    if _publisher_task:
        _publisher_task.cancel()
        try:
            await _publisher_task
        except asyncio.CancelledError:
            pass
    if _consumer_thread:
        _consumer_thread.join(timeout=5)
    if producer:
        producer.flush()
    logger.info("camera_simulator_stopped")


app = FastAPI(title="Camera Simulator", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if producer is None:
        raise HTTPException(status_code=503, detail="Producer not initialized")
    return {"status": "ready"}


@app.get("/cameras")
async def list_cameras() -> list[dict[str, Any]]:
    return [
        {
            "camera_id": s.camera_id,
            "mode": s.mode,
            "interval": s.current_interval,
            "last_frame_time": s.last_published if s.last_published > 0 else None,
        }
        for s in camera_states.values()
    ]


@app.post("/cameras/{camera_id}/publish")
async def manual_publish(camera_id: str) -> dict[str, Any]:
    """Manually trigger a frame publish for testing."""
    if camera_id not in camera_states:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    if producer is None:
        raise HTTPException(status_code=503, detail="Producer not initialized")

    state = camera_states[camera_id]
    state.frame_sequence += 1
    publish_frame(
        producer,
        camera_id=state.camera_id,
        asset_id=state.asset_id,
        image_path=state.image_path,
        frame_sequence=state.frame_sequence,
        escalated=state.mode == "escalated",
    )
    state.last_published = time.time()

    return {
        "camera_id": camera_id,
        "frame_sequence": state.frame_sequence,
        "escalated": state.mode == "escalated",
    }
