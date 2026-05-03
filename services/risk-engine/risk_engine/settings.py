# This project was developed with assistance from AI tools.

from __future__ import annotations

from grid_common.settings import ServiceSettings


class RiskEngineSettings(ServiceSettings):
    """Risk Engine configuration."""

    otel_service_name: str = "risk-engine"
    kafka_consumer_group_id: str = "risk-engine"
    weight_weather: float = 0.40
    weight_age: float = 0.25
    weight_vegetation: float = 0.20
    weight_inspection: float = 0.15
    ice_density_factor: float = 0.85
    wind_max_mps: float = 30.0
    ice_max_mm: float = 25.0
    end_of_line_multiplier: float = 1.3
    max_asset_age_years: int = 50
    max_days_since_inspection: int = 365
    min_vegetation_clearance_m: float = 1.0
    host: str = "0.0.0.0"
    port: int = 8080
