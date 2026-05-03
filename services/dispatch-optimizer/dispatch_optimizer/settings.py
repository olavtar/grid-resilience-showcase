# This project was developed with assistance from AI tools.

from __future__ import annotations

from grid_common.settings import ServiceSettings


class DispatchOptimizerSettings(ServiceSettings):
    """Dispatch Optimizer configuration."""

    otel_service_name: str = "dispatch-optimizer"
    kafka_consumer_group_id: str = "dispatch-optimizer"
    cuopt_url: str = "http://localhost:5000"
    cuopt_timeout_seconds: float = 10.0
    approval_mode: str = "manual"
    storm_auto_min_priority: str = "critical"
    host: str = "0.0.0.0"
    port: int = 8080
