# This project was developed with assistance from AI tools.

from __future__ import annotations

from grid_common.settings import ServiceSettings


class DefectDetectorSettings(ServiceSettings):
    """Defect Detector configuration."""

    otel_service_name: str = "defect-detector"
    kafka_consumer_group_id: str = "defect-detector"
    vllm_base_url: str = "http://localhost:8000"
    vllm_model: str = "cosmos-reason-2"
    confidence_threshold: float = 0.70
    vllm_timeout_seconds: float = 30.0
    host: str = "0.0.0.0"
    port: int = 8080
