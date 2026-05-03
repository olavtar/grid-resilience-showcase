#!/usr/bin/env python3
# This project was developed with assistance from AI tools.

"""Cosmos Transfer 2.5 weather augmentation pipeline for camera imagery."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import yaml

DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"


def load_config(config_path: Path) -> dict:
    """Load augmentation config from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def augment_image(
    image_path: Path,
    output_path: Path,
    cosmos_url: str,
    weather_params: dict,
) -> bool:
    """Send an image to Cosmos Transfer 2.5 for weather augmentation."""
    image_bytes = image_path.read_bytes()

    # Cosmos Transfer 2.5 API — image2image generation with conditioning
    # The exact API contract depends on the NGC container version.
    # Reference: Cosmos Cookbook "ITS Weather Augmentation" recipe.
    request = {
        "image": image_bytes.hex(),
        "conditioning": {
            "weather": weather_params.get("weather", "overcast, ice accumulation, freezing rain"),
            "lighting": weather_params.get("lighting", "twilight, overcast"),
            "surface": weather_params.get("surface", "ice, frost"),
        },
        "num_inference_steps": weather_params.get("num_inference_steps", 30),
        "strength": weather_params.get("strength", 0.6),
    }

    try:
        response = httpx.post(
            f"{cosmos_url}/v1/image2image",
            json=request,
            timeout=120.0,
        )
        response.raise_for_status()

        result = response.json()
        augmented_bytes = bytes.fromhex(result["image"])
        output_path.write_bytes(augmented_bytes)
        print(f"  Augmented: {image_path.name} → {output_path.name}")
        return True
    except (httpx.RequestError, httpx.HTTPStatusError, KeyError) as e:
        print(f"  FAILED: {image_path.name} — {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Cosmos Transfer 2.5 weather augmentation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cosmos-url", default="http://localhost:8080")
    parser.add_argument("--input-dir", type=Path, default=Path("data/images/base"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/images/augmented"))
    args = parser.parse_args()

    config = load_config(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    weather_params = config.get("weather_conditioning", {})
    image_extensions = {".jpg", ".jpeg", ".png"}

    images = sorted(f for f in args.input_dir.iterdir() if f.suffix.lower() in image_extensions)

    if not images:
        print(f"No images found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Augmenting {len(images)} images with Cosmos Transfer 2.5")
    print(f"  Input:  {args.input_dir}")
    print(f"  Output: {args.output_dir}")
    print(f"  Weather: {weather_params.get('weather', 'default')}")

    success = 0
    for image_path in images:
        output_path = args.output_dir / f"augmented_{image_path.name}"
        if augment_image(image_path, output_path, args.cosmos_url, weather_params):
            success += 1

    print(f"\nComplete: {success}/{len(images)} images augmented")
    if success < len(images):
        sys.exit(1)


if __name__ == "__main__":
    main()
