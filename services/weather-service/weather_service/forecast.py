# This project was developed with assistance from AI tools.

"""Forecast logic — calls CorrDiff NIM and publishes weather events."""

from __future__ import annotations

import io
import math
import tarfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np
import structlog
from confluent_kafka import Producer

from grid_common.events import (
    GridCell,
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

CORRDIFF_OUTPUT_VARS = ["u10m", "v10m", "t2m", "tp", "csnow", "cicep", "cfrzr", "crain"]

CONUS_LAT_START = 21.138
CONUS_LAT_END = 52.615
CONUS_LON_START = -134.09
CONUS_LON_END = -60.919
CONUS_NLAT = 1059
CONUS_NLON = 1799


def _pixel_to_latlon(row: int, col: int) -> tuple[float, float]:
    """Convert CorrDiff output pixel to lat/lon."""
    lat = CONUS_LAT_START + (CONUS_LAT_END - CONUS_LAT_START) * row / (CONUS_NLAT - 1)
    lon = CONUS_LON_START + (CONUS_LON_END - CONUS_LON_START) * col / (CONUS_NLON - 1)
    return lat, lon


def _extract_piedmont_cells(
    output_array: np.ndarray, settings: WeatherServiceSettings
) -> list[GridCell]:
    """Extract grid cells within the Piedmont NC corridor from CorrDiff output."""
    row_start = int(
        (settings.corridor_lat_min - CONUS_LAT_START)
        / (CONUS_LAT_END - CONUS_LAT_START)
        * (CONUS_NLAT - 1)
    )
    row_end = int(
        (settings.corridor_lat_max - CONUS_LAT_START)
        / (CONUS_LAT_END - CONUS_LAT_START)
        * (CONUS_NLAT - 1)
    )
    col_start = int(
        (settings.corridor_lon_min - CONUS_LON_START)
        / (CONUS_LON_END - CONUS_LON_START)
        * (CONUS_NLON - 1)
    )
    col_end = int(
        (settings.corridor_lon_max - CONUS_LON_START)
        / (CONUS_LON_END - CONUS_LON_START)
        * (CONUS_NLON - 1)
    )

    row_start = max(0, row_start)
    row_end = min(CONUS_NLAT - 1, row_end)
    col_start = max(0, col_start)
    col_end = min(CONUS_NLON - 1, col_end)

    step = max(1, (row_end - row_start) // 4)

    cells = []
    for r in range(row_start, row_end + 1, step):
        for c in range(col_start, col_end + 1, step):
            lat, lon = _pixel_to_latlon(r, c)
            u10m = float(output_array[0, r, c])
            v10m = float(output_array[1, r, c])
            t2m = float(output_array[2, r, c])
            tp = float(max(0.0, output_array[3, r, c]))
            csnow = bool(output_array[4, r, c] > 0.5)
            cicep = bool(output_array[5, r, c] > 0.5)
            cfrzr = bool(output_array[6, r, c] > 0.5)
            crain = bool(output_array[7, r, c] > 0.5)
            cells.append(
                GridCell(
                    lat=round(lat, 4),
                    lon=round(lon, 4),
                    t2m_k=t2m,
                    u10m_mps=u10m,
                    v10m_mps=v10m,
                    tp_mm=tp,
                    csnow=csnow,
                    cicep=cicep,
                    cfrzr=cfrzr,
                    crain=crain,
                )
            )

    logger.info(
        "piedmont_cells_extracted",
        count=len(cells),
        rows=f"{row_start}-{row_end}",
        cols=f"{col_start}-{col_end}",
    )
    return cells


async def run_forecast(
    settings: WeatherServiceSettings,
    producer: Producer,
    client: httpx.AsyncClient,
) -> list[WeatherForecast]:
    """Run CorrDiff NIM inference and publish forecasts to Kafka."""
    trace_id = uuid.uuid4().hex

    input_path = Path(settings.gfs_data_dir) / "corrdiff_inputs.npy"
    if not input_path.exists():
        logger.error("gfs_input_not_found", path=str(input_path))
        raise FileNotFoundError(f"Pre-staged GFS data not found: {input_path}")

    logger.info("calling_corrdiff_nim", url=settings.corrdiff_nim_url, input=str(input_path))

    with open(input_path, "rb") as f:
        response = await client.post(
            f"{settings.corrdiff_nim_url}/v1/infer",
            data={"samples": "1", "steps": "8", "seed": "42"},
            files={"input_array": ("input_array", f)},
            headers={"accept": "application/x-tar"},
            timeout=180.0,
        )

    if response.status_code != 200:
        logger.error(
            "corrdiff_inference_failed", status=response.status_code, body=response.text[:200]
        )
        raise RuntimeError(f"CorrDiff inference failed: {response.status_code}")

    logger.info("corrdiff_inference_complete", size=len(response.content))

    tar_bytes = io.BytesIO(response.content)
    with tarfile.open(fileobj=tar_bytes, mode="r") as tar:
        members = tar.getnames()
        logger.info("corrdiff_output_members", members=members)

        npy_name = next((m for m in members if m.endswith(".npy")), None)
        if npy_name is None:
            raise RuntimeError("No .npy file in CorrDiff output tar")

        npy_file = tar.extractfile(npy_name)
        if npy_file is None:
            raise RuntimeError(f"Could not extract {npy_name}")
        output_array = np.load(io.BytesIO(npy_file.read()))

    logger.info("corrdiff_output_shape", shape=output_array.shape)

    grid_cells = _extract_piedmont_cells(output_array, settings)

    now = datetime.now(tz=UTC)
    forecast = WeatherForecast(
        forecast_hour=0,
        valid_time=now,
        grid_cells=grid_cells,
        resolution_km=3.0,
        model="corrdiff",
        trace_id=trace_id,
        source_service="weather-service",
    )

    forecasts = [forecast]

    for fc in forecasts:
        publish_event(producer, "grid.weather.forecast", fc)
        alerts = _evaluate_alerts(fc, trace_id)
        for alert in alerts:
            publish_event(producer, "grid.weather.alerts", alert)

    ops = OpsEvent(
        category="weather",
        title="Earth-2 CorrDiff forecast published",
        detail=f"Live 3km downscaled forecast: {len(grid_cells)} grid cells "
        f"over Piedmont NC corridor.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="weather-service",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()

    logger.info("forecast_published", cells=len(grid_cells))
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
    if not lats:
        return alerts

    lat_min = min(lats)
    lat_max = max(lats)
    lon_min = min(lons)
    lon_max = max(lons)

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
                message=f"Wind speeds up to {max_wind:.1f} m/s forecast.",
                forecast_hour=forecast.forecast_hour,
                trace_id=trace_id,
                source_service="weather-service",
                affected_area_lat_min=lat_min,
                affected_area_lat_max=lat_max,
                affected_area_lon_min=lon_min,
                affected_area_lon_max=lon_max,
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
                message="Freezing rain detected in forecast.",
                forecast_hour=forecast.forecast_hour,
                trace_id=trace_id,
                source_service="weather-service",
                affected_area_lat_min=lat_min,
                affected_area_lat_max=lat_max,
                affected_area_lon_min=lon_min,
                affected_area_lon_max=lon_max,
            )
        )

    if max_ice_mm > ICE_ACCUMULATION_ALERT_MM:
        alerts.append(
            WeatherAlert(
                alert_type="ice_accumulation",
                severity=Severity.CRITICAL,
                message=f"Ice accumulation up to {max_ice_mm:.1f}mm forecast.",
                forecast_hour=forecast.forecast_hour,
                trace_id=trace_id,
                source_service="weather-service",
                affected_area_lat_min=lat_min,
                affected_area_lat_max=lat_max,
                affected_area_lon_min=lon_min,
                affected_area_lon_max=lon_max,
            )
        )

    return alerts
