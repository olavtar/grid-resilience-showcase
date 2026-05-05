# This project was developed with assistance from AI tools.

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dispatch_optimizer.consumer import consumer_loop
from dispatch_optimizer.guardrails import validate_dispatch_plan
from dispatch_optimizer.optimizer import run_optimization
from dispatch_optimizer.settings import DispatchOptimizerSettings
from dispatch_optimizer.state import DispatchPlan, DispatchState
from grid_common.events import DispatchAssignment, DispatchStatus, OpsEvent, Severity
from grid_common.kafka import create_producer, publish_event
from grid_common.logging import setup_logging

logger = structlog.get_logger()

settings = DispatchOptimizerSettings()
producer = None
http_client: httpx.AsyncClient | None = None
state = DispatchState()
lock = threading.Lock()
optimize_trigger = threading.Event()


class ApprovalRequest(BaseModel):
    """Body for approve/reject endpoints."""

    justification: str


class OverrideRequest(BaseModel):
    """Body for override endpoint."""

    justification: str
    overrides: list[dict[str, Any]]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global producer, http_client
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    producer = create_producer(settings)
    http_client = httpx.AsyncClient()

    thread = threading.Thread(
        target=consumer_loop,
        args=(settings, producer, state, lock, optimize_trigger),
        daemon=True,
    )
    thread.start()
    logger.info("dispatch_optimizer_started")
    yield
    if producer:
        producer.flush()
    if http_client:
        await http_client.aclose()
    logger.info("dispatch_optimizer_stopped")


app = FastAPI(title="Dispatch Optimizer", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if producer is None or http_client is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    try:
        resp = await http_client.get(
            f"{settings.cuopt_url}/cuopt/health",
            timeout=3.0,
        )
        resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=503, detail="cuOpt not reachable") from None
    return {"status": "ready"}


@app.post("/dispatch/reset")
async def reset_dispatch() -> dict[str, str]:
    """Clear all pending work orders and plans."""
    with lock:
        state.pending_work_orders.clear()
        state.active_plans.clear()
        state.active_faults.clear()
    return {"status": "reset"}


@app.post("/dispatch/optimize")
async def optimize() -> dict[str, Any]:
    """Trigger optimization from pending work orders."""
    if http_client is None or producer is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    with lock:
        work_orders = list(state.pending_work_orders.values())
        crews = list(state.crew_cache)
        active_faults = list(state.active_faults)
        risk_scores = dict(state.risk_scores)

    if not work_orders:
        raise HTTPException(status_code=400, detail="No pending work orders")
    if not crews:
        raise HTTPException(status_code=400, detail="No available crews")

    plan_id, assignments, solve_time_ms = await run_optimization(
        work_orders,
        crews,
        http_client,
        settings,
    )

    # Build lookup dicts for guardrails
    wo_dict = {wo.get("work_order_id", wo.get("event_id", "")): wo for wo in work_orders}
    crew_dict = {c.get("crew_id") or c.get("id", ""): c for c in crews}

    pre_guard_dicts = [a.model_dump() for a in assignments]
    guardrails_results, guardrails_messages = validate_dispatch_plan(
        pre_guard_dicts,
        wo_dict,
        crew_dict,
        active_faults,
        risk_scores,
    )

    # Apply guardrails results to assignments
    for a in assignments:
        gr = guardrails_results.get(a.crew_id, "pass")
        a.guardrails_result = gr
        msg = guardrails_messages.get(a.crew_id)
        if msg:
            a.guardrails_message = msg

    assignment_dicts = [a.model_dump() for a in assignments]

    plan = DispatchPlan(
        plan_id=plan_id,
        assignments=assignment_dicts,
        status="pending_approval",
        created_at=datetime.utcnow(),
        cuopt_solve_time_ms=solve_time_ms,
        guardrails_results=guardrails_results,
    )

    with lock:
        state.active_plans[plan_id] = plan

    # Publish assignments to Kafka
    for a in assignments:
        publish_event(producer, "grid.crew.dispatch", a, key=a.crew_id)

    ops = OpsEvent(
        category="dispatch",
        title=f"Dispatch plan {plan_id[:8]} created with {len(assignments)} assignments",
        detail=f"Solve time: {solve_time_ms:.0f}ms",
        severity=Severity.INFO,
        source_service="dispatch-optimizer",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()

    with lock:
        state.pending_work_orders.clear()

    # Auto-approve in storm-auto mode for qualifying priorities
    if settings.approval_mode == "storm-auto":
        min_priority = settings.storm_auto_min_priority
        qualifying = all(
            wo_dict.get(a.work_order_id, {}).get("priority", "") == min_priority
            for a in assignments
        )
        if qualifying and all(v != "block" for v in guardrails_results.values()):
            plan.status = "approved"
            for a in assignments:
                a.status = DispatchStatus.APPROVED
                publish_event(producer, "grid.crew.dispatch", a, key=a.crew_id)
            producer.flush()

    return {
        "plan_id": plan_id,
        "status": plan.status,
        "assignments": len(assignments),
        "cuopt_solve_time_ms": round(solve_time_ms, 1),
        "guardrails_results": guardrails_results,
    }


@app.post("/dispatch/approve/{plan_id}")
async def approve_plan(plan_id: str, body: ApprovalRequest) -> dict[str, Any]:
    """Approve a pending dispatch plan."""
    if producer is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    with lock:
        plan = state.active_plans.get(plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Plan status is {plan.status}")

    plan.status = "approved"

    for assignment_dict in plan.assignments:
        a = DispatchAssignment(
            **{k: v for k, v in assignment_dict.items() if k != "timestamp"},
            status=DispatchStatus.APPROVED,
            dispatcher_justification=body.justification,
            source_service="dispatch-optimizer",
        )
        publish_event(producer, "grid.crew.dispatch", a, key=a.crew_id)

    producer.flush()
    logger.info("plan_approved", plan_id=plan_id)

    return {"plan_id": plan_id, "status": "approved"}


@app.post("/dispatch/reject/{plan_id}")
async def reject_plan(plan_id: str, body: ApprovalRequest) -> dict[str, Any]:
    """Reject a pending dispatch plan."""
    with lock:
        plan = state.active_plans.get(plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Plan status is {plan.status}")

    plan.status = "rejected"
    logger.info("plan_rejected", plan_id=plan_id, justification=body.justification)

    return {"plan_id": plan_id, "status": "rejected"}


@app.post("/dispatch/override/{plan_id}")
async def override_plan(plan_id: str, body: OverrideRequest) -> dict[str, Any]:
    """Approve with crew reassignments."""
    if producer is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    with lock:
        plan = state.active_plans.get(plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != "pending_approval":
        raise HTTPException(status_code=409, detail=f"Plan status is {plan.status}")

    # Apply overrides: each override is {"work_order_id": ..., "crew_id": ...}
    override_map = {o["work_order_id"]: o["crew_id"] for o in body.overrides}
    for assignment_dict in plan.assignments:
        wo_id = assignment_dict.get("work_order_id", "")
        if wo_id in override_map:
            assignment_dict["crew_id"] = override_map[wo_id]

    plan.status = "approved"

    for assignment_dict in plan.assignments:
        a = DispatchAssignment(
            **{k: v for k, v in assignment_dict.items() if k != "timestamp"},
            status=DispatchStatus.APPROVED,
            dispatcher_justification=body.justification,
            source_service="dispatch-optimizer",
        )
        publish_event(producer, "grid.crew.dispatch", a, key=a.crew_id)

    producer.flush()
    logger.info("plan_overridden", plan_id=plan_id, overrides=len(body.overrides))

    return {"plan_id": plan_id, "status": "approved", "overrides_applied": len(body.overrides)}


@app.get("/dispatch/plans")
async def list_plans() -> list[dict[str, Any]]:
    """List all dispatch plans."""
    with lock:
        plans = list(state.active_plans.values())
    return [
        {
            "plan_id": p.plan_id,
            "status": p.status,
            "assignments": len(p.assignments),
            "created_at": p.created_at.isoformat(),
            "cuopt_solve_time_ms": round(p.cuopt_solve_time_ms, 1),
            "guardrails_results": p.guardrails_results,
        }
        for p in plans
    ]


@app.get("/dispatch/plans/{plan_id}")
async def get_plan(plan_id: str) -> dict[str, Any]:
    """Get a single dispatch plan with full details."""
    with lock:
        plan = state.active_plans.get(plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "plan_id": plan.plan_id,
        "status": plan.status,
        "assignments": plan.assignments,
        "created_at": plan.created_at.isoformat(),
        "cuopt_solve_time_ms": round(plan.cuopt_solve_time_ms, 1),
        "guardrails_results": plan.guardrails_results,
    }
