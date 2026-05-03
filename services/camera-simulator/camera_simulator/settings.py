# This project was developed with assistance from AI tools.

from __future__ import annotations

from grid_common.settings import ServiceSettings


class CameraSimulatorSettings(ServiceSettings):
    """Camera Simulator configuration."""

    otel_service_name: str = "camera-simulator"
    kafka_consumer_group_id: str = "camera-simulator"
    image_dir: str = "data/images"
    host: str = "0.0.0.0"
    port: int = 8080
