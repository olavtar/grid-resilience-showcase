# This project was developed with assistance from AI tools.

"""Open the substation USD scene on Kit startup."""

import omni.usd

stage_path = "/opt/nvidia/isaac-sim/scene/substation.usd"
omni.usd.get_context().open_stage(stage_path)
print(f"[grid-resilience] Opened stage: {stage_path}")
