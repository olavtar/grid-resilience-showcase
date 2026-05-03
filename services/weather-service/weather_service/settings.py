# This project was developed with assistance from AI tools.

from __future__ import annotations

from grid_common.settings import ServiceSettings


class WeatherServiceSettings(ServiceSettings):
    """Weather Service configuration."""

    otel_service_name: str = "weather-service"
    kafka_consumer_group_id: str = "weather-service"
    corrdiff_nim_url: str = "http://localhost:8000"
    gfs_data_dir: str = "data/gfs"
    corridor_lat_min: float = 36.05
    corridor_lat_max: float = 36.12
    corridor_lon_min: float = -79.55
    corridor_lon_max: float = -79.40
    host: str = "0.0.0.0"
    port: int = 8080
