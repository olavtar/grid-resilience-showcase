# This project was developed with assistance from AI tools.

from __future__ import annotations

from typing import Any

import structlog
from confluent_kafka import Producer

from grid_common.events import CameraEscalate, InspectionFrame
from grid_common.kafka import publish_event

logger = structlog.get_logger()


def publish_frame(
    producer: Producer,
    camera_id: str,
    asset_id: str,
    image_path: str,
    frame_sequence: int,
    escalated: bool,
    trace_id: str | None = None,
) -> None:
    """Publish an InspectionFrame event to the camera frames topic."""
    frame = InspectionFrame(
        camera_id=camera_id,
        asset_id=asset_id,
        image_url=image_path,
        frame_sequence=frame_sequence,
        escalated=escalated,
        trace_id=trace_id,
        source_service="camera-simulator",
    )
    publish_event(producer, "grid.cameras.frames", frame, key=camera_id)
    producer.poll(0)
    logger.info(
        "frame_published",
        camera_id=camera_id,
        sequence=frame_sequence,
        escalated=escalated,
    )


def handle_escalate_event(
    event_data: dict[str, Any],
    camera_states: dict[str, Any],
) -> list[str]:
    """Switch matching cameras to escalated mode. Returns escalated camera IDs."""
    escalate = CameraEscalate(**{k: v for k, v in event_data.items() if not k.startswith("_")})
    escalated_ids: list[str] = []
    for cam_id in escalate.camera_ids:
        if cam_id in camera_states:
            state = camera_states[cam_id]
            state.mode = "escalated"
            state.current_interval = state.escalated_interval
            escalated_ids.append(cam_id)
            logger.info(
                "camera_escalated",
                camera_id=cam_id,
                interval=state.escalated_interval,
                reason=escalate.reason,
            )
    return escalated_ids
