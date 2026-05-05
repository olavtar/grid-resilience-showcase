# This project was developed with assistance from AI tools.

"""Open the substation USD scene and start the data-driven extension."""

import asyncio
import sys

import omni.kit.app
import omni.usd

stage_path = "/opt/nvidia/isaac-sim/scene/substation.usd"
omni.usd.get_context().open_stage(stage_path)
print(f"[grid-resilience] Opened stage: {stage_path}")

sys.path.insert(0, "/opt/nvidia/isaac-sim/exts/grid.resilience.data")


async def _start_extension():
    for _ in range(10):
        await omni.kit.app.get_app().next_update_async()

    try:
        from grid.resilience.data.extension import GridResilienceDataExtension

        ext = GridResilienceDataExtension()
        ext.on_startup("grid.resilience.data-0.1.0")
        print("[grid-resilience] Data extension started manually")
    except Exception as e:
        print(f"[grid-resilience] Extension start failed: {e}")
        import traceback

        traceback.print_exc()


_task = asyncio.ensure_future(_start_extension())  # noqa: RUF006
