# This project was developed with assistance from AI tools.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DispatchPlan:
    """Optimized dispatch plan from cuOpt with guardrails results."""

    plan_id: str
    assignments: list[dict[str, Any]]
    status: str  # pending_approval, approved, rejected
    created_at: datetime
    cuopt_solve_time_ms: float
    guardrails_results: dict[str, str]  # crew_id -> pass/warn/block


@dataclass
class DispatchState:
    """Mutable in-memory state for the dispatch optimizer."""

    pending_work_orders: dict[str, Any] = field(default_factory=dict)
    active_plans: dict[str, DispatchPlan] = field(default_factory=dict)
    crew_cache: list[dict[str, Any]] = field(default_factory=list)
    risk_scores: dict[str, float] = field(default_factory=dict)
    active_faults: list[str] = field(default_factory=list)
