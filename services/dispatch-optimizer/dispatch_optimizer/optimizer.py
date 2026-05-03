# This project was developed with assistance from AI tools.

from __future__ import annotations

import math
import time
import uuid
from typing import Any

import httpx
import structlog

from dispatch_optimizer.settings import DispatchOptimizerSettings
from grid_common.events import DispatchAssignment, DispatchStatus

logger = structlog.get_logger()

PRIORITY_WEIGHTS: dict[str, int] = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 1,
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


def build_cuopt_request(
    work_orders: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    settings: DispatchOptimizerSettings,
) -> dict[str, Any]:
    """Assemble cuOpt REST API payload."""
    crew_locations = [(c["lat"], c["lon"]) for c in crews]
    wo_locations = [(wo["lat"], wo["lon"]) for wo in work_orders]
    cost_matrix = build_cost_matrix(crew_locations, wo_locations)

    n_crews = len(crews)
    n_tasks = len(work_orders)

    # Task indices start after crew depot indices
    task_indices = list(range(n_crews, n_crews + n_tasks))

    priorities = [PRIORITY_WEIGHTS.get(wo.get("priority", "medium"), 4) for wo in work_orders]

    service_times = [wo.get("estimated_duration_minutes", 60) for wo in work_orders]

    return {
        "cost_matrix_data": {"data": {"0": cost_matrix}},
        "fleet_data": {
            "vehicle_ids": [c["crew_id"] for c in crews],
            "vehicle_locations": [[i, i] for i in range(n_crews)],
            "capacities": [[8] * n_crews],
        },
        "task_data": {
            "task_ids": [wo["work_order_id"] for wo in work_orders],
            "task_locations": task_indices,
            "demand": [[1] * n_tasks],
            "service_times": service_times,
            "priorities": priorities,
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
    """POST optimization request to cuOpt."""
    url = f"{settings.cuopt_url}/cuopt/request"
    response = await client.post(
        url,
        json=request_payload,
        timeout=settings.cuopt_timeout_seconds + 5.0,
    )
    response.raise_for_status()
    result: dict[str, Any] = response.json()
    return result


def parse_cuopt_response(
    response: dict[str, Any],
    work_orders: list[dict[str, Any]],
    crews: list[dict[str, Any]],
    plan_id: str,
    solve_time_ms: float,
) -> list[DispatchAssignment]:
    """Parse cuOpt solution into DispatchAssignment events."""
    assignments: list[DispatchAssignment] = []
    wo_by_id = {wo["work_order_id"]: wo for wo in work_orders}
    crew_by_id = {c["crew_id"]: c for c in crews}

    routes = response.get("response", {}).get("solver_response", {}).get("vehicle_data", {})

    for vehicle_id, route_data in routes.items():
        task_ids = route_data.get("task_id", [])
        arrival_stamps = route_data.get("arrival_stamp", [])

        crew = crew_by_id.get(vehicle_id, {})
        crew_lat = crew.get("lat", 0.0)
        crew_lon = crew.get("lon", 0.0)

        for idx, task_id in enumerate(task_ids):
            wo = wo_by_id.get(task_id)
            if wo is None:
                continue

            route_polyline = [
                [crew_lat, crew_lon],
                [wo["lat"], wo["lon"]],
            ]

            eta = arrival_stamps[idx] if idx < len(arrival_stamps) else None

            assignments.append(
                DispatchAssignment(
                    plan_id=plan_id,
                    crew_id=vehicle_id,
                    work_order_id=task_id,
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
