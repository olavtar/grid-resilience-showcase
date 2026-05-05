# This project was developed with assistance from AI tools.

"""Generate a weather forecast raster overlay from grid cell data."""

from __future__ import annotations

import io
import threading
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

_latest_overlay: bytes | None = None
_overlay_bounds: tuple[float, float, float, float] | None = None
_lock = threading.Lock()


def _interpolate_grid(
    lats: list[float],
    lons: list[float],
    values: list[float],
    bounds: tuple[float, float, float, float],
    resolution: int = 128,
) -> np.ndarray:
    """Interpolate sparse grid cells to a regular raster."""
    lat_min, lat_max, lon_min, lon_max = bounds
    grid_y = np.linspace(lat_min, lat_max, resolution)
    grid_x = np.linspace(lon_min, lon_max, resolution)
    gx, gy = np.meshgrid(grid_x, grid_y)

    if len(lats) < 3:
        return np.zeros((resolution, resolution))

    try:
        from scipy.interpolate import griddata

        points = np.array(list(zip(lons, lats, strict=False)))
        grid = griddata(points, np.array(values), (gx, gy), method="linear", fill_value=0.0)
        grid = np.clip(grid, 0, None)
        return np.flipud(grid)
    except ImportError:
        return np.zeros((resolution, resolution))


def _render_overlay(
    presence_grid: np.ndarray,
    freezing_grid: np.ndarray,
    intensity_grid: np.ndarray,
) -> bytes:
    """Render weather coverage as a transparent RGBA PNG."""
    h, w = presence_grid.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    for r in range(h):
        for c in range(w):
            p = presence_grid[r, c]
            if p < 0.15:
                continue

            fz = freezing_grid[r, c]
            intensity = min(intensity_grid[r, c], 1.0)
            alpha = int(min(p, 1.0) * 220)

            if fz > 0.3:
                base_r, base_g, base_b = 120, 40, 200
                boost_r, boost_g, boost_b = 60, -20, 40
            else:
                base_r, base_g, base_b = 40, 60, 220
                boost_r, boost_g, boost_b = -20, -30, 35

            rgba[r, c, 0] = min(255, int(base_r + boost_r * intensity))
            rgba[r, c, 1] = min(255, max(0, int(base_g + boost_g * intensity)))
            rgba[r, c, 2] = min(255, int(base_b + boost_b * intensity))
            rgba[r, c, 3] = alpha

    img = Image.fromarray(rgba, "RGBA")
    img = img.resize((512, 512), Image.Resampling.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def update_overlay(forecast_data: dict[str, Any]) -> None:
    """Update the cached overlay from a WeatherForecast event."""
    global _latest_overlay, _overlay_bounds

    grid_cells = forecast_data.get("grid_cells", [])
    if not grid_cells:
        return

    lats = [c["lat"] for c in grid_cells]
    lons = [c["lon"] for c in grid_cells]

    presence = []
    freezing = []
    intensity = []
    for c in grid_cells:
        has_wx = any(
            [
                c.get("cfrzr", False),
                c.get("cicep", False),
                c.get("csnow", False),
                c.get("crain", False),
            ]
        )
        tp = c.get("tp_mm", 0.0)
        presence.append(1.0 if has_wx or tp > 0.01 else 0.0)
        freezing.append(1.0 if c.get("cfrzr", False) or c.get("cicep", False) else 0.0)
        intensity.append(min(tp / 2.0, 1.0))

    padding = 0.02
    bounds = (
        min(lats) - padding,
        max(lats) + padding,
        min(lons) - padding,
        max(lons) + padding,
    )

    res = 128
    presence_grid = _interpolate_grid(lats, lons, presence, bounds, res)
    freezing_grid = _interpolate_grid(lats, lons, freezing, bounds, res)
    intensity_grid = _interpolate_grid(lats, lons, intensity, bounds, res)

    png_bytes = _render_overlay(presence_grid, freezing_grid, intensity_grid)

    with _lock:
        _latest_overlay = png_bytes
        _overlay_bounds = bounds


def get_overlay() -> tuple[bytes | None, tuple[float, float, float, float] | None]:
    """Return the latest overlay PNG and its geographic bounds."""
    with _lock:
        return _latest_overlay, _overlay_bounds
