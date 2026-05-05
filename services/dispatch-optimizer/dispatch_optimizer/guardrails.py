# This project was developed with assistance from AI tools.

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


def validate_dispatch_plan(
    assignments: list[dict[str, Any]],
    work_orders: dict[str, Any],
    crews: dict[str, Any],
    active_faults: list[str],
    risk_scores: dict[str, float],
) -> tuple[dict[str, str], dict[str, str]]:
    """Run safety checks. Returns (crew_id -> result, crew_id -> message)."""
    results: dict[str, str] = {}
    messages: dict[str, str] = {}

    for assignment in assignments:
        crew_id = assignment.get("crew_id", "")
        wo_id = assignment.get("work_order_id", "")
        wo = work_orders.get(wo_id, {})
        crew = crews.get(crew_id, {})

        result = "pass"
        msg = ""

        if asset_id := wo.get("asset_id", ""):
            if asset_id in active_faults:
                result = "block"
                msg = f"Active fault zone on {asset_id}"
                logger.warning("guardrail_fault_zone", crew_id=crew_id, asset_id=asset_id)

        if result != "block":
            required = set(wo.get("required_skills", []))
            crew_skills = set(crew.get("skills", []) + crew.get("certifications", []))
            missing = required - crew_skills
            if missing:
                result = "block"
                msg = f"Missing: {', '.join(sorted(missing))}"
                logger.warning("guardrail_certification", crew_id=crew_id, missing=list(missing))

        if result != "block":
            remaining_shift = crew.get("remaining_shift_minutes", 480)
            travel_time = assignment.get("eta_minutes") or 0
            duration = wo.get("estimated_duration_minutes", 60)
            buffer = remaining_shift - travel_time - duration
            if buffer < 0:
                result = "block"
                msg = "Exceeds remaining shift time"
                logger.warning("guardrail_shift_exceeded", crew_id=crew_id, buffer=buffer)
            elif buffer < 30 and result == "pass":
                result = "warn"
                msg = "Tight shift buffer"
                logger.info("guardrail_shift_tight", crew_id=crew_id, buffer=buffer)

        if result not in ("block",):
            score = risk_scores.get(wo.get("asset_id", ""), 0.0)
            if score > 0.9 and result == "pass":
                result = "warn"
                msg = "High weather risk at location"
                logger.info("guardrail_weather_risk", crew_id=crew_id, risk_score=score)

        results[crew_id] = result
        if msg:
            messages[crew_id] = msg

    return results, messages
