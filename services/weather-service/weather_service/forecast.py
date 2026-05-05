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
import pyproj
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

CONUS_NLAT = 1056
CONUS_NLON = 1792

# HRRR Lambert Conformal Conic projection (CorrDiff output grid)
_HRRR_PROJ = pyproj.Proj(proj="lcc", lat_1=38.5, lat_2=38.5, lat_0=38.5, lon_0=-97.5, R=6371229)
_HRRR_DX = 3000.0
_HRRR_DY = 3000.0
_HRRR_NX = 1799
_HRRR_NY = 1059
_X0, _Y0 = _HRRR_PROJ(-122.719528, 21.138123)
_CD_COL_OFFSET = (_HRRR_NX - CONUS_NLON) // 2
_CD_ROW_OFFSET = (_HRRR_NY - CONUS_NLAT) // 2


def _pixel_to_latlon(row: int, col: int) -> tuple[float, float]:
    """Convert CorrDiff output pixel to lat/lon via HRRR Lambert Conformal."""
    x = _X0 + (col + _CD_COL_OFFSET) * _HRRR_DX
    y = _Y0 + (row + _CD_ROW_OFFSET) * _HRRR_DY
    lon, lat = _HRRR_PROJ(x, y, inverse=True)
    return float(lat), float(lon)


def _latlon_to_pixel(lat: float, lon: float) -> tuple[int, int]:
    """Convert lat/lon to CorrDiff output pixel indices."""
    x, y = _HRRR_PROJ(lon, lat)
    col = round((x - _X0) / _HRRR_DX - _CD_COL_OFFSET)
    row = round((y - _Y0) / _HRRR_DY - _CD_ROW_OFFSET)
    return row, col


def _extract_piedmont_cells(
    output_array: np.ndarray, settings: WeatherServiceSettings
) -> list[GridCell]:
    """Extract grid cells within an expanded Burlington NC region from CorrDiff output."""
    padding = 0.5
    lat_min = settings.corridor_lat_min - padding
    lat_max = settings.corridor_lat_max + padding
    lon_min = settings.corridor_lon_min - padding
    lon_max = settings.corridor_lon_max + padding

    nlat = output_array.shape[-2]
    nlon = output_array.shape[-1]

    r_sw, c_sw = _latlon_to_pixel(lat_min, lon_min)
    r_ne, c_ne = _latlon_to_pixel(lat_max, lon_max)
    row_start = max(0, min(r_sw, r_ne))
    row_end = min(nlat - 1, max(r_sw, r_ne))
    col_start = max(0, min(c_sw, c_ne))
    col_end = min(nlon - 1, max(c_sw, c_ne))

    arr = output_array
    while arr.ndim > 3:
        arr = arr[0]

    cells = []
    for r in range(row_start, row_end + 1):
        for c in range(col_start, col_end + 1):
            lat, lon = _pixel_to_latlon(r, c)
            cells.append(
                GridCell(
                    lat=round(lat, 4),
                    lon=round(lon, 4),
                    t2m_k=float(arr[2, r, c]),
                    u10m_mps=float(arr[0, r, c]),
                    v10m_mps=float(arr[1, r, c]),
                    tp_mm=float(max(0.0, arr[3, r, c])),
                    csnow=bool(arr[4, r, c] > 0.5),
                    cicep=bool(arr[5, r, c] > 0.5),
                    cfrzr=bool(arr[6, r, c] > 0.5),
                    crain=bool(arr[7, r, c] > 0.5),
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

    cache_path = Path("/cache/corrdiff_output_cache.npy")
    np.save(str(cache_path), output_array)
    logger.info("corrdiff_output_cached", path=str(cache_path))

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
        f"over Burlington NC corridor.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="weather-service",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()

    logger.info("forecast_published", cells=len(grid_cells))
    return forecasts


def publish_cached_forecast(
    settings: WeatherServiceSettings,
    producer: Producer,
) -> list[WeatherForecast] | None:
    """Republish the last CorrDiff forecast from cached output."""
    cache_path = Path("/cache/corrdiff_output_cache.npy")
    if not cache_path.exists():
        logger.warning("no_cached_forecast")
        return None

    output_array = np.load(str(cache_path))
    grid_cells = _extract_piedmont_cells(output_array, settings)

    trace_id = uuid.uuid4().hex
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
        f"over Burlington NC corridor.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="weather-service",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()

    logger.info("cached_forecast_published", cells=len(grid_cells))
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
