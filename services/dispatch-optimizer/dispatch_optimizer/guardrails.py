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
) -> dict[str, str]:
    """Run safety checks on each assignment, returning crew_id -> pass/warn/block."""
    results: dict[str, str] = {}

    for assignment in assignments:
        crew_id = assignment.get("crew_id", "")
        wo_id = assignment.get("work_order_id", "")
        wo = work_orders.get(wo_id, {})
        crew = crews.get(crew_id, {})

        result = "pass"

        # 1. Fault zone: no crew dispatched to segment with active fault
        asset_id = wo.get("asset_id", "")
        if asset_id in active_faults:
            result = "block"
            logger.warning("guardrail_fault_zone", crew_id=crew_id, asset_id=asset_id)

        # 2. Certification check
        if result != "block":
            required = set(wo.get("required_skills", []))
            crew_certs = set(crew.get("certifications", []))
            missing = required - crew_certs
            if missing:
                result = "block"
                logger.warning(
                    "guardrail_certification",
                    crew_id=crew_id,
                    missing=list(missing),
                )

        # 3. Shift time check
        if result != "block":
            remaining_shift = crew.get("remaining_shift_minutes", 480)
            travel_time = assignment.get("eta_minutes") or 0
            duration = wo.get("estimated_duration_minutes", 60)
            buffer = remaining_shift - travel_time - duration
            if buffer < 0:
                result = "block"
                logger.warning("guardrail_shift_exceeded", crew_id=crew_id, buffer=buffer)
            elif buffer < 30 and result == "pass":
                result = "warn"
                logger.info("guardrail_shift_tight", crew_id=crew_id, buffer=buffer)

        # 4. Weather red-zone check
        if result not in ("block",):
            score = risk_scores.get(asset_id, 0.0)
            if score > 0.9 and result == "pass":
                result = "warn"
                logger.info("guardrail_weather_risk", crew_id=crew_id, risk_score=score)

        results[crew_id] = result

    return results
