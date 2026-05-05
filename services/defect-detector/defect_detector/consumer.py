# This project was developed with assistance from AI tools.

"""Kafka consumer loop — consumes camera frames, runs detection, publishes findings."""

from __future__ import annotations

import asyncio
import base64
import json
import threading
from collections import deque
from pathlib import Path

import httpx
import psycopg
import structlog
from confluent_kafka import Producer

from defect_detector.detector import analyze_frame
from defect_detector.settings import DefectDetectorSettings
from grid_common.events import (
    DefectFinding,
    InspectionFinding,
    OpsEvent,
    Severity,
    WorkOrder,
    WorkOrderPriority,
)
from grid_common.kafka import create_consumer, publish_event

logger = structlog.get_logger()

SKILL_MAP: dict[str, list[str]] = {
    "cracked_crossarm": ["lineman", "bucket_truck"],
    "damaged_insulator": ["lineman", "bucket_truck"],
    "vegetation_encroachment": ["vegetation"],
    "leaning_pole": ["lineman"],
    "missing_hardware": ["lineman"],
    "corrosion": ["lineman"],
    "ice_loading": ["lineman"],
}

PRIORITY_MAP: dict[str, WorkOrderPriority] = {
    "critical": WorkOrderPriority.CRITICAL,
    "major": WorkOrderPriority.HIGH,
    "warning": WorkOrderPriority.MEDIUM,
    "info": WorkOrderPriority.LOW,
}


def _load_asset_locations(dsn: str) -> dict[str, tuple[float, float]]:
    """Load asset lat/lon from PostgreSQL for work order location fields."""
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, lat, lon FROM assets")
            return {row[0]: (row[1], row[2]) for row in cur.fetchall()}


def _create_work_order(
    finding: DefectFinding,
    camera_id: str,
    asset_id: str,
    asset_locations: dict[str, tuple[float, float]],
    trace_id: str | None,
) -> WorkOrder:
    """Create a work order from an actionable finding."""
    lat, lon = asset_locations.get(asset_id, (0.0, 0.0))
    skills = SKILL_MAP.get(finding.defect_type, ["lineman"])
    priority = PRIORITY_MAP.get(finding.severity.value, WorkOrderPriority.MEDIUM)

    return WorkOrder(
        asset_id=asset_id,
        title=f"{finding.defect_type.replace('_', ' ').title()} — {asset_id}",
        description=finding.description,
        priority=priority,
        required_skills=skills,
        lat=lat,
        lon=lon,
        estimated_duration_minutes=90,
        trace_id=trace_id,
        source_service="defect-detector",
    )


def consumer_loop(
    settings: DefectDetectorSettings,
    producer: Producer,
    findings_buffer: deque[InspectionFinding],
    lock: threading.Lock,
) -> None:
    """Consume camera frames, run detection, publish findings and work orders."""
    consumer = create_consumer(
        settings,
        group_id="defect-detector",
        topics=["grid.cameras.frames"],
    )

    asset_locations = _load_asset_locations(settings.dsn)
    logger.info("asset_locations_loaded", count=len(asset_locations))

    loop = asyncio.new_event_loop()
    client = httpx.AsyncClient(timeout=settings.vllm_timeout_seconds)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("consumer_error", error=str(msg.error()))
                continue

            raw = msg.value()
            if raw is None:
                continue
            try:
                data = json.loads(raw.decode())
                camera_id = data["camera_id"]
                asset_id = data["asset_id"]
                image_url = data["image_url"]
                frame_event_id = data.get("event_id", "")
                trace_id = data.get("trace_id")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("frame_parse_error", error=str(e))
                continue

            findings, latency_ms = loop.run_until_complete(
                analyze_frame(image_url, client, settings)
            )

            encoded_image = None
            if findings:
                image_path = Path(image_url)
                if image_path.exists():
                    encoded_image = base64.b64encode(image_path.read_bytes()).decode()

            inspection = InspectionFinding(
                camera_id=camera_id,
                asset_id=asset_id,
                frame_event_id=frame_event_id,
                findings=findings,
                inference_latency_ms=latency_ms,
                image_data=encoded_image,
                trace_id=trace_id,
                source_service="defect-detector",
            )
            publish_event(producer, "grid.cameras.findings", inspection, key=camera_id)

            with lock:
                findings_buffer.append(inspection)

            for finding in findings:
                if finding.severity in (Severity.CRITICAL, Severity.MAJOR):
                    ops = OpsEvent(
                        category="camera",
                        title=f"Defect detected: {finding.defect_type}",
                        detail=f"{camera_id} on {asset_id}: {finding.description}",
                        severity=finding.severity,
                        related_asset_id=asset_id,
                        trace_id=trace_id,
                        source_service="defect-detector",
                    )
                    publish_event(producer, "grid.ops.events", ops)

            producer.flush()

            logger.info(
                "frame_processed",
                camera_id=camera_id,
                findings_count=len(findings),
                latency_ms=round(latency_ms, 1),
            )
    finally:
        loop.run_until_complete(client.aclose())
        loop.close()
        consumer.close()
