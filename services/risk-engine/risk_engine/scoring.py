# This project was developed with assistance from AI tools.

"""Asset risk scoring algorithm from plan Section 8.2."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from grid_common.events import AssetRiskScore, GridCell, RiskBreakdown
from risk_engine.settings import RiskEngineSettings


def nearest_grid_cell(lat: float, lon: float, grid_cells: list[GridCell]) -> GridCell | None:
    """Find the nearest grid cell to an asset by Euclidean distance."""
    if not grid_cells:
        return None
    return min(grid_cells, key=lambda c: (c.lat - lat) ** 2 + (c.lon - lon) ** 2)


def weather_exposure_score(
    asset_lat: float,
    asset_lon: float,
    is_end_of_line: bool,
    grid_cells: list[GridCell],
    settings: RiskEngineSettings,
) -> float:
    """Compute weather exposure sub-score for an asset."""
    cell = nearest_grid_cell(asset_lat, asset_lon, grid_cells)
    if cell is None:
        return 0.0

    wind_speed = math.sqrt(cell.u10m_mps**2 + cell.v10m_mps**2)
    wind_score = min(wind_speed / settings.wind_max_mps, 1.0)

    ice_accumulation = cell.tp_mm * settings.ice_density_factor if cell.cfrzr else 0.0
    ice_score = min(ice_accumulation / settings.ice_max_mm, 1.0)

    multiplier = settings.end_of_line_multiplier if is_end_of_line else 1.0
    return min((wind_score * 0.4 + ice_score * 0.6) * multiplier, 1.0)


def age_score(
    install_year: int | None,
    expected_lifespan: int | None,
    settings: RiskEngineSettings,
) -> float:
    """Compute age-based risk sub-score."""
    if install_year is None:
        return 0.5
    years_old = datetime.now().year - install_year
    lifespan = expected_lifespan or settings.max_asset_age_years
    return min(years_old / lifespan, 1.0)


def vegetation_score(
    clearance_m: float | None,
    settings: RiskEngineSettings,
) -> float:
    """Compute vegetation proximity risk sub-score."""
    if clearance_m is None:
        return 0.5
    max_safe = settings.min_vegetation_clearance_m * 3.0
    return max(1.0 - (clearance_m / max_safe), 0.0)


def inspection_recency_score(
    last_inspection_date: date | None,
    settings: RiskEngineSettings,
) -> float:
    """Compute inspection recency risk sub-score."""
    if last_inspection_date is None:
        return 0.8
    days_since = (date.today() - last_inspection_date).days
    return min(days_since / settings.max_days_since_inspection, 1.0)


def compute_asset_risk(
    asset: dict[str, Any],
    grid_cells: list[GridCell],
    forecast_hour: int,
    settings: RiskEngineSettings,
) -> AssetRiskScore:
    """Compute composite risk score with explainable breakdown for one asset."""
    w = weather_exposure_score(
        asset["lat"],
        asset["lon"],
        asset.get("is_end_of_line", False),
        grid_cells,
        settings,
    )
    a = age_score(
        asset.get("install_year"),
        asset.get("expected_lifespan_years"),
        settings,
    )
    v = vegetation_score(asset.get("vegetation_clearance_m"), settings)

    insp_date = asset.get("last_inspection_date")
    if isinstance(insp_date, str):
        insp_date = date.fromisoformat(insp_date)
    i = inspection_recency_score(insp_date, settings)

    composite = (
        settings.weight_weather * w
        + settings.weight_age * a
        + settings.weight_vegetation * v
        + settings.weight_inspection * i
    )

    return AssetRiskScore(
        asset_id=asset["id"],
        asset_type=asset["asset_type"],
        composite_score=round(composite, 4),
        breakdown=RiskBreakdown(
            weather_exposure=round(w, 4),
            age=round(a, 4),
            vegetation=round(v, 4),
            inspection_recency=round(i, 4),
        ),
        forecast_hour=forecast_hour,
        source_service="risk-engine",
    )
