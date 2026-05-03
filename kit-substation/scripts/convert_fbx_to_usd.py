#!/usr/bin/env python3
# This project was developed with assistance from AI tools.

"""Convert FBX to USD using omni.kit.asset_converter (run via isaac-sim.sh --exec)."""

from __future__ import annotations

import asyncio
import os
import sys

import omni.kit.app
import omni.kit.asset_converter


def progress_callback(current_step: int, total_steps: int) -> None:
    print(f"  Converting: step {current_step}/{total_steps}")


async def convert(input_path: str, output_path: str) -> bool:
    """Convert an FBX file to USD."""
    converter = omni.kit.asset_converter.get_instance()

    context = omni.kit.asset_converter.AssetConverterContext()
    context.ignore_animations = True
    context.embed_textures = True
    context.convert_fbx_to_y_up = True

    task = converter.create_converter_task(
        input_path,
        output_path,
        progress_callback,
        asset_converter_context=context,
    )
    success = await task.wait_until_finished()

    if not success:
        detailed_status = task.get_status()
        print(f"Conversion failed: {detailed_status}", file=sys.stderr)
    return success


repo_root = os.environ.get(
    "REPO_ROOT",
    "/home/jary/redhat/git/grid-resilience-showcase",
)
input_path = os.environ.get(
    "INPUT_FBX",
    os.path.join(repo_root, "assets/purchased/substation/utu_substation_pack.fbx"),
)
output_path = os.environ.get(
    "OUTPUT_USD",
    os.path.join(repo_root, "assets/purchased/substation/substation.usd"),
)

print(f"Converting: {input_path}")
print(f"Output:     {output_path}")

result = asyncio.ensure_future(convert(input_path, output_path))

while not result.done():
    omni.kit.app.get_app().update()

if result.result():
    print(f"Conversion complete: {output_path}")
else:
    print("Conversion failed", file=sys.stderr)

omni.kit.app.get_app().post_quit()
