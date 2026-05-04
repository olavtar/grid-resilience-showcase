# This project was developed with assistance from AI tools.

from __future__ import annotations

from grid_common.settings import ServiceSettings


class ScenarioEngineSettings(ServiceSettings):
    """Scenario Engine configuration."""

    otel_service_name: str = "scenario-engine"
    kafka_consumer_group_id: str = "scenario-engine"
    scenario_dir: str = "data/scenarios"
    weather_service_url: str = "http://weather-service.grid-ops-services.svc.cluster.local:8080"
    host: str = "0.0.0.0"
    port: int = 8080
