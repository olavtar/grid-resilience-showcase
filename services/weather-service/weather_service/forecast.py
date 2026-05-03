# This project was developed with assistance from AI tools.

"""Forecast logic — calls CorrDiff NIM and publishes weather events."""

from __future__ import annotations

import math
import uuid

import httpx
import structlog
from confluent_kafka import Producer

from grid_common.events import (
    OpsEvent,
    Severity,
    WeatherAlert,
    WeatherForecast,
)
from grid_common.kafka import publish_event
from weather_service.settings import WeatherServiceSettings

logger = structlog.get_logger()

ICE_DENSITY_FACTOR = 0.85
WIND_ALERT_THRESHOLD_MPS = 20.0
FREEZING_RAIN_PRECIP_THRESHOLD_MM = 5.0
ICE_ACCUMULATION_ALERT_MM = 10.0


async def run_forecast(
    settings: WeatherServiceSettings,
    producer: Producer,
    client: httpx.AsyncClient,
) -> list[WeatherForecast]:
    """Run CorrDiff NIM inference and publish forecasts to Kafka."""
    trace_id = uuid.uuid4().hex

    # TODO: implement full CorrDiff NIM API call chain
    # 1. Load pre-staged GFS data from settings.gfs_data_dir
    # 2. Submit to CorrDiff NIM at settings.corrdiff_nim_url
    # 3. Extract grid cells within corridor bounding box
    # For now, this is the integration point — the structure is ready
    # for the NIM client code once we validate the API contract.

    response = await client.get(f"{settings.corrdiff_nim_url}/v1/health/ready")
    if response.status_code != 200:
        logger.error("corrdiff_nim_not_ready", status=response.status_code)
        raise RuntimeError("CorrDiff NIM not ready")

    logger.info("corrdiff_nim_ready", url=settings.corrdiff_nim_url)

    # Placeholder: construct forecast from NIM response
    # This will be replaced with actual NIM output parsing
    forecasts: list[WeatherForecast] = []

    # Publish forecasts and evaluate alerts
    for forecast in forecasts:
        publish_event(producer, "grid.weather.forecast", forecast)
        alerts = _evaluate_alerts(forecast, trace_id)
        for alert in alerts:
            publish_event(producer, "grid.weather.alerts", alert)

    if forecasts:
        ops = OpsEvent(
            category="weather",
            title="Earth-2 forecast published",
            detail=f"CorrDiff 3km forecast: {len(forecasts)} timesteps, "
            f"{sum(len(f.grid_cells) for f in forecasts)} grid cells.",
            severity=Severity.INFO,
            trace_id=trace_id,
            source_service="weather-service",
        )
        publish_event(producer, "grid.ops.events", ops)

    producer.flush()
    return forecasts


async def warmup_nim(
    settings: WeatherServiceSettings,
    client: httpx.AsyncClient,
) -> bool:
    """Warm up CorrDiff NIM with throwaway inference passes."""
    try:
        response = await client.get(f"{settings.corrdiff_nim_url}/v1/health/ready")
        return response.status_code == 200
    except httpx.RequestError as e:
        logger.warning("corrdiff_warmup_failed", error=str(e))
        return False


def _evaluate_alerts(
    forecast: WeatherForecast,
    trace_id: str,
) -> list[WeatherAlert]:
    """Check forecast grid cells against alert thresholds."""
    alerts: list[WeatherAlert] = []

    lats = [c.lat for c in forecast.grid_cells]
    lons = [c.lon for c in forecast.grid_cells]
    lat_min = min(lats) if lats else 0.0
    lat_max = max(lats) if lats else 0.0
    lon_min = min(lons) if lons else 0.0
    lon_max = max(lons) if lons else 0.0

    max_wind = 0.0
    has_freezing_rain = False
    max_ice_mm = 0.0

    for cell in forecast.grid_cells:
        wind_speed = math.sqrt(cell.u10m_mps**2 + cell.v10m_mps**2)
        max_wind = max(max_wind, wind_speed)

        if cell.cfrzr:
            has_freezing_rain = True
            ice_mm = cell.tp_mm * ICE_DENSITY_FACTOR
            max_ice_mm = max(max_ice_mm, ice_mm)

    if max_wind > WIND_ALERT_THRESHOLD_MPS:
        alerts.append(
            WeatherAlert(
                alert_type="high_wind",
                severity=Severity.WARNING,
                message=f"Wind speeds up to {max_wind:.1f} m/s forecast "
                f"at hour {forecast.forecast_hour}.",
                affected_area_lat_min=lat_min,
                affected_area_lat_max=lat_max,
                affected_area_lon_min=lon_min,
                affected_area_lon_max=lon_max,
                forecast_hour=forecast.forecast_hour,
                trace_id=trace_id,
                source_service="weather-service",
            )
        )

    if (
        has_freezing_rain
        and max((c.tp_mm for c in forecast.grid_cells if c.cfrzr), default=0.0)
        > FREEZING_RAIN_PRECIP_THRESHOLD_MM
    ):
        alerts.append(
            WeatherAlert(
                alert_type="freezing_rain",
                severity=Severity.WARNING,
                message=f"Freezing rain expected at hour {forecast.forecast_hour}.",
                affected_area_lat_min=lat_min,
                affected_area_lat_max=lat_max,
                affected_area_lon_min=lon_min,
                affected_area_lon_max=lon_max,
                forecast_hour=forecast.forecast_hour,
                trace_id=trace_id,
                source_service="weather-service",
            )
        )

    if max_ice_mm > ICE_ACCUMULATION_ALERT_MM:
        alerts.append(
            WeatherAlert(
                alert_type="ice_accumulation",
                severity=Severity.CRITICAL,
                message=f"Ice accumulation up to {max_ice_mm:.1f}mm forecast "
                f"at hour {forecast.forecast_hour}.",
                affected_area_lat_min=lat_min,
                affected_area_lat_max=lat_max,
                affected_area_lon_min=lon_min,
                affected_area_lon_max=lon_max,
                forecast_hour=forecast.forecast_hour,
                trace_id=trace_id,
                source_service="weather-service",
            )
        )

    return alerts
