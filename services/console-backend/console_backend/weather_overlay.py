# This project was developed with assistance from AI tools.

"""Generate a weather forecast raster overlay from grid cell data."""

from __future__ import annotations

import io
import threading
from typing import Any

import numpy as np
from PIL import Image

_latest_overlay: bytes | None = None
_overlay_bounds: tuple[float, float, float, float] | None = None
_lock = threading.Lock()

PRECIP_COLORS = np.array(
    [
        [0, 0, 0, 0],  # no precip — transparent
        [100, 149, 237, 80],  # light rain — cornflower blue
        [65, 105, 225, 100],  # moderate rain — royal blue
        [0, 0, 205, 120],  # heavy rain — medium blue
        [138, 43, 226, 130],  # freezing rain — blue violet
        [148, 0, 211, 150],  # heavy freezing rain — dark violet
        [199, 21, 133, 160],  # ice pellets — medium violet red
    ],
    dtype=np.uint8,
)


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
        grid = griddata(points, np.array(values), (gx, gy), method="cubic", fill_value=0.0)
        grid = np.clip(grid, 0, None)
        return np.flipud(grid)
    except ImportError:
        result = np.zeros((resolution, resolution))
        for i, (lat, lon, val) in enumerate(zip(lats, lons, values, strict=False)):
            r = int((lat - lat_min) / (lat_max - lat_min) * (resolution - 1))
            c = int((lon - lon_min) / (lon_max - lon_min) * (resolution - 1))
            r = min(max(r, 0), resolution - 1)
            c = min(max(c, 0), resolution - 1)
            spread = max(resolution // 8, 3)
            for dr in range(-spread, spread + 1):
                for dc in range(-spread, spread + 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < resolution and 0 <= cc < resolution:
                        dist = (dr * dr + dc * dc) ** 0.5
                        weight = max(0, 1.0 - dist / spread)
                        result[resolution - 1 - rr, cc] = max(
                            result[resolution - 1 - rr, cc], val * weight
                        )
        return result


def _render_overlay(
    precip_grid: np.ndarray,
    freezing_grid: np.ndarray,
    wind_grid: np.ndarray,
) -> bytes:
    """Render precipitation data as a transparent RGBA PNG."""
    h, w = precip_grid.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    max_precip = max(precip_grid.max(), 1.0)
    norm_precip = precip_grid / max_precip

    for r in range(h):
        for c in range(w):
            p = norm_precip[r, c]
            fz = freezing_grid[r, c]
            wind = wind_grid[r, c]

            if p < 0.05:
                continue

            if fz > 0.5:
                idx = min(int(3 + p * 3), 6)
            else:
                idx = min(int(p * 3), 3)

            color = PRECIP_COLORS[idx].copy()
            wind_boost = min(wind / 25.0, 1.0) * 30
            color[3] = min(int(color[3] + wind_boost), 200)
            rgba[r, c] = color

    img = Image.fromarray(rgba, "RGBA")
    img = img.resize((512, 512), Image.Resampling.LANCZOS)
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
    precip = [c.get("tp_mm", 0.0) for c in grid_cells]
    freezing = [1.0 if c.get("cfrzr", False) else 0.0 for c in grid_cells]
    wind = [(c.get("u10m_mps", 0.0) ** 2 + c.get("v10m_mps", 0.0) ** 2) ** 0.5 for c in grid_cells]

    padding = 0.02
    bounds = (
        min(lats) - padding,
        max(lats) + padding,
        min(lons) - padding,
        max(lons) + padding,
    )

    res = 128
    precip_grid = _interpolate_grid(lats, lons, precip, bounds, res)
    freezing_grid = _interpolate_grid(lats, lons, freezing, bounds, res)
    wind_grid = _interpolate_grid(lats, lons, wind, bounds, res)

    png_bytes = _render_overlay(precip_grid, freezing_grid, wind_grid)

    with _lock:
        _latest_overlay = png_bytes
        _overlay_bounds = bounds


def get_overlay() -> tuple[bytes | None, tuple[float, float, float, float] | None]:
    """Return the latest overlay PNG and its geographic bounds."""
    with _lock:
        return _latest_overlay, _overlay_bounds
