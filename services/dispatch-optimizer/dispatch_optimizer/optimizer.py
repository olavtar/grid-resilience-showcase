# This project was developed with assistance from AI tools.

from __future__ import annotations

import asyncio
import math
import time
import uuid
from typing import Any

import httpx
import structlog

from dispatch_optimizer.settings import DispatchOptimizerSettings
from grid_common.events import DispatchAssignment, DispatchStatus

logger = structlog.get_logger()

PRIORITY_WEIGHTS: dict[str, float] = {
    "critical": 10.0,
    "high": 7.0,
    "medium": 4.0,
    "low": 1.0,
}

CUOPT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "CLIENT-VERSION": "custom",
}


def build_cost_matrix(
    crew_locations: list[tuple[float, float]],
    work_order_locations: list[tuple[float, float]],
) -> list[list[float]]:
    """Build Euclidean distance matrix (km) between all locations."""
    all_locations = crew_locations + work_order_locations
    n = len(all_locations)
    matrix: list[list[float]] = []
    for i in range(n):
        row: list[float] = []
        for j in range(n):
            if i == j:
                row.append(0.0)
            else:
                lat_i, lon_i = all_locations[i]
                lat_j, lon_j = all_locations[j]
                dx = (lon_j - lon_i) * 85.0
                dy = (lat_j - lat_i) * 111.0
                row.append(math.sqrt(dx * dx + dy * dy))
        matrix.append(row)
    return matrix


def _build_skill_match(
    work_orders: list[dict[str, Any]],
    crews: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build order_vehicle_match: for each task, list eligible vehicle indices."""
    match: list[dict[str, Any]] = []
    for task_idx, wo in enumerate(work_orders):
        required = set(wo.get("required_skills", []))
        eligible: list[int] = []
        for crew_idx, crew in enumerate(crews):
            crew_skills = set(crew.get("skills", []) + crew.get("certifications", []))
            if required.issubset(crew_skills):
                eligible.append(crew_idx)
        if not eligible:
            eligible = list(range(len(crews)))
        match.append({"order_id": task_idx, "vehicle_ids": eligible})
    return match


def build_cuopt_request(
    work_orders: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    settings: DispatchOptimizerSettings,
) -> dict[str, Any]:
    """Assemble cuOpt REST API payload."""
    crew_locations = [
        (c.get("current_lat") or c.get("lat", 0), c.get("current_lon") or c.get("lon", 0))
        for c in crews
    ]
    wo_locations = [(wo["lat"], wo["lon"]) for wo in work_orders]
    cost_matrix = build_cost_matrix(crew_locations, wo_locations)

    avg_speed_kmph = 30.0
    mobilization_min = 15.0
    time_matrix = [
        [d / avg_speed_kmph * 60.0 + mobilization_min for d in row] for row in cost_matrix
    ]

    n_crews = len(crews)
    n_tasks = len(work_orders)

    task_indices = list(range(n_crews, n_crews + n_tasks))

    prizes = [PRIORITY_WEIGHTS.get(wo.get("priority", "medium"), 4.0) for wo in work_orders]
    service_times = [wo.get("estimated_duration_minutes", 60) for wo in work_orders]

    vehicle_ids = [c.get("crew_id") or c.get("id", "") for c in crews]
    order_vehicle_match = _build_skill_match(work_orders, crews)

    return {
        "cost_matrix_data": {"data": {"0": cost_matrix}},
        "travel_time_matrix_data": {"data": {"0": time_matrix}},
        "fleet_data": {
            "vehicle_ids": vehicle_ids,
            "vehicle_locations": [[i, i] for i in range(n_crews)],
            "capacities": [[1] * n_crews],
            "vehicle_max_times": [180.0] * n_crews,
        },
        "task_data": {
            "task_ids": [wo["work_order_id"] for wo in work_orders],
            "task_locations": task_indices,
            "demand": [[1] * n_tasks],
            "service_times": service_times,
            "prizes": prizes,
            "order_vehicle_match": order_vehicle_match,
        },
        "solver_config": {
            "time_limit": settings.cuopt_timeout_seconds,
        },
    }


async def call_cuopt(
    request_payload: dict[str, Any],
    client: httpx.AsyncClient,
    settings: DispatchOptimizerSettings,
) -> dict[str, Any]:
    """POST optimization request to cuOpt and poll for solution."""
    base_url = settings.cuopt_url
    response = await client.post(
        f"{base_url}/cuopt/request",
        json=request_payload,
        headers=CUOPT_HEADERS,
        timeout=settings.cuopt_timeout_seconds + 5.0,
    )
    response.raise_for_status()
    submit_result: dict[str, Any] = response.json()
    req_id = submit_result.get("reqId")
    if not req_id:
        return submit_result

    logger.info("cuopt_submitted", req_id=req_id)

    for _ in range(30):
        await asyncio.sleep(1)
        poll = await client.get(
            f"{base_url}/cuopt/solution/{req_id}",
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        poll.raise_for_status()
        result: dict[str, Any] = poll.json()
        if "response" in result:
            logger.info("cuopt_solved", req_id=req_id)
            return result
        logger.info("cuopt_polling", req_id=req_id)

    logger.warning("cuopt_timeout", req_id=req_id)
    return submit_result


def parse_cuopt_response(
    response: dict[str, Any],
    work_orders: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    plan_id: str,
    solve_time_ms: float,
) -> list[DispatchAssignment]:
    """Parse cuOpt solution into DispatchAssignment events."""
    assignments: list[DispatchAssignment] = []
    assigned_tasks: set[str] = set()
    wo_by_id = {wo["work_order_id"]: wo for wo in work_orders}
    crew_by_id = {c.get("crew_id") or c.get("id", ""): c for c in crews}

    routes = response.get("response", {}).get("solver_response", {}).get("vehicle_data", {})

    for vehicle_id, route_data in routes.items():
        task_ids = route_data.get("task_id", [])
        arrival_stamps = route_data.get("arrival_stamp", [])

        crew = crew_by_id.get(vehicle_id, {})
        crew_lat = crew.get("current_lat") or crew.get("lat", 0.0)
        crew_lon = crew.get("current_lon") or crew.get("lon", 0.0)

        for idx, task_id in enumerate(task_ids):
            wo = wo_by_id.get(task_id)
            if wo is None or task_id in assigned_tasks:
                continue
            assigned_tasks.add(task_id)

            route_polyline = [
                [crew_lat, crew_lon],
                [wo["lat"], wo["lon"]],
            ]

            eta_raw = arrival_stamps[idx] if idx < len(arrival_stamps) else None
            eta = round(eta_raw) if eta_raw is not None else None

            assignments.append(
                DispatchAssignment(
                    plan_id=plan_id,
                    crew_id=vehicle_id,
                    work_order_id=task_id,
                    work_order_title=wo.get("title", task_id),
                    status=DispatchStatus.PENDING_APPROVAL,
                    route_polyline=route_polyline,
                    eta_minutes=eta,
                    cuopt_solve_time_ms=solve_time_ms,
                    source_service="dispatch-optimizer",
                )
            )

    return assignments


async def run_optimization(
    work_orders: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    client: httpx.AsyncClient,
    settings: DispatchOptimizerSettings,
) -> tuple[str, list[DispatchAssignment], float]:
    """Run full optimization cycle: build request, call cuOpt, parse response."""
    plan_id = str(uuid.uuid4())
    payload = build_cuopt_request(work_orders, crews, settings)

    start = time.monotonic()
    response = await call_cuopt(payload, client, settings)
    solve_time_ms = (time.monotonic() - start) * 1000.0

    assignments = parse_cuopt_response(response, work_orders, crews, plan_id, solve_time_ms)

    logger.info(
        "optimization_complete",
        plan_id=plan_id,
        assignments=len(assignments),
        solve_time_ms=round(solve_time_ms, 1),
    )

    return plan_id, assignments, solve_time_ms
