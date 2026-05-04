# This project was developed with assistance from AI tools.

"""Detection prompt template for Cosmos Reason 2-8B."""

from __future__ import annotations

DETECTION_PROMPT = (
    "You are a utility infrastructure monitoring AI examining a frame from "
    "a fixed camera on distribution grid infrastructure.\n\n"
    "Check for ALL of these conditions — report every one you see:\n"
    "1. Cracked, broken, or split crossarms\n"
    "2. Damaged or missing insulators\n"
    "3. Vegetation encroachment — any tree branch touching, resting on, "
    "crossing over, or growing within arm's reach of power line conductors\n"
    "4. Leaning or tilted poles\n"
    "5. Missing hardware (bolts, clamps, guy wire attachments)\n"
    "6. Visible corrosion on metal components\n"
    "7. Ice accumulation on conductors or equipment\n\n"
    "For EACH condition found, respond with JSON:\n"
    '{"findings": [{"defect_type": "vegetation_encroachment", '
    '"severity": "major", "confidence": 0.95, '
    '"description": "one sentence", '
    '"recommended_action": "one sentence"}]}\n\n'
    'If nothing is found, return: {"findings": []}'
)
