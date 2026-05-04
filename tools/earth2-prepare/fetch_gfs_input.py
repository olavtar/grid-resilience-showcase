#!/usr/bin/env python3
# This project was developed with assistance from AI tools.

"""Fetch and prepare GEFS input data for CorrDiff NIM inference."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import s3fs
import torch

original_init = s3fs.S3FileSystem.__init__


def _patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
    if "config_kwargs" not in kwargs:
        kwargs["config_kwargs"] = {}
    kwargs["config_kwargs"].setdefault("s3", {})
    kwargs["config_kwargs"]["s3"]["use_accelerate_endpoint"] = False
    original_init(self, *args, **kwargs)


s3fs.S3FileSystem.__init__ = _patched_init  # type: ignore[method-assign]

from earth2studio.data import GEFS_FX, GEFS_FX_721x1440  # noqa: E402

GEFS_SELECT_VARIABLES = ["u10m", "v10m", "t2m", "r2m", "sp", "msl", "tcwv"]

GEFS_VARIABLES = [
    "u1000", "u925", "u850", "u700", "u500", "u250",
    "v1000", "v925", "v850", "v700", "v500", "v250",
    "z1000", "z925", "z850", "z700", "z500", "z200",
    "t1000", "t925", "t850", "t700", "t500", "t100",
    "r1000", "r925", "r850", "r700", "r500", "r100",
]


def fetch_input_gefs(
    time: datetime,
    lead_time: timedelta,
    content_dtype: str = "float32",
) -> np.ndarray:
    """Fetch GEFS data and prepare CorrDiff input array."""
    dtype = np.dtype(getattr(np, content_dtype))

    ds_gefs = GEFS_FX(cache=True)
    ds_gefs_select = GEFS_FX_721x1440(cache=True, member="gec00")

    print("Fetching high-res select data...")
    select_data = ds_gefs_select(time, lead_time, GEFS_SELECT_VARIABLES)
    select_data = select_data.values[:, 0, :, 148:277, 900:1201].astype(dtype)

    print("Fetching pressure level data...")
    pressure_data = ds_gefs(time, lead_time, GEFS_VARIABLES)
    pressure_data = torch.nn.functional.interpolate(
        torch.Tensor(pressure_data.values),
        (len(GEFS_VARIABLES), 721, 1440),
        mode="nearest",
    ).numpy()
    pressure_data = pressure_data[:, 0, :, 148:277, 900:1201].astype(dtype)

    lead_hour = (
        int(lead_time.total_seconds() // (3 * 3600))
        * np.ones((1, 1, 129, 301)).astype(dtype)
    )

    return np.concatenate([select_data, pressure_data, lead_hour], axis=1)[None]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch GEFS input for CorrDiff")
    parser.add_argument("--date", default="2024-01-14", help="YYYY-MM-DD")
    parser.add_argument("--lead-hours", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("data/gfs/corrdiff_inputs.npy"))
    args = parser.parse_args()

    time = datetime.strptime(args.date, "%Y-%m-%d")
    lead = timedelta(hours=args.lead_hours)

    print(f"Fetching GEFS data for {time} + {lead}")
    input_array = fetch_input_gefs(time, lead)
    print(f"Input shape: {input_array.shape}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(args.output), input_array)
    print(f"Saved to {args.output} ({args.output.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
