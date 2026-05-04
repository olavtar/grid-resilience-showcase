# This project was developed with assistance from AI tools.

from __future__ import annotations

import json
import threading
from typing import Any

import psycopg
import structlog
from confluent_kafka import Producer

from dispatch_optimizer.settings import DispatchOptimizerSettings
from dispatch_optimizer.state import DispatchState
from grid_common.kafka import create_consumer

logger = structlog.get_logger()

_TOPICS = [
    "grid.crew.work-orders",
    "grid.faults.detected",
    "grid.assets.risk-scores",
]


def _load_crews(dsn: str) -> list[dict[str, Any]]:
    """Load available crews from PostgreSQL."""
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, current_lat, current_lon, status, "
                "skills, certifications, shift_start, shift_end "
                "FROM crews WHERE status = 'available'"
            )
            cols = [desc[0] for desc in (cur.description or [])]
            rows = [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
            # certifications is stored as a JSON array in PG
            for row in rows:
                if isinstance(row.get("certifications"), str):
                    row["certifications"] = json.loads(row["certifications"])
            return rows


def consumer_loop(
    settings: DispatchOptimizerSettings,
    producer: Producer,
    state: DispatchState,
    lock: threading.Lock,
    optimize_trigger: threading.Event,
) -> None:
    """Consume work orders, faults, and risk scores."""
    consumer = create_consumer(
        settings,
        group_id="dispatch-optimizer",
        topics=_TOPICS,
    )

    try:
        crews = _load_crews(settings.dsn)
        with lock:
            state.crew_cache = crews
        logger.info("crews_loaded", count=len(crews))
    except Exception:
        logger.exception("crew_load_failed")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("consumer_error", error=str(msg.error()))
                continue

            topic = msg.topic()
            try:
                raw = msg.value()
                if raw is None:
                    continue
                data = json.loads(raw.decode())
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning("message_parse_error", topic=topic, error=str(e))
                continue

            if topic == "grid.crew.work-orders":
                wo_id = data.get("work_order_id", data.get("event_id", ""))
                with lock:
                    state.pending_work_orders[wo_id] = data
                logger.info("work_order_received", work_order_id=wo_id)

                # Auto-trigger for critical/high when enough pending
                priority = data.get("priority", "medium")
                if priority in ("critical", "high"):
                    with lock:
                        pending_count = len(state.pending_work_orders)
                    if pending_count >= 2:
                        optimize_trigger.set()

            elif topic == "grid.faults.detected":
                segment_id = data.get("segment_id", "")
                with lock:
                    if segment_id and segment_id not in state.active_faults:
                        state.active_faults.append(segment_id)
                logger.info("fault_received", segment_id=segment_id)

                # Re-optimize in storm-auto mode
                if settings.approval_mode == "storm-auto":
                    optimize_trigger.set()

            elif topic == "grid.assets.risk-scores":
                asset_id = data.get("asset_id", "")
                score = data.get("composite_score", 0.0)
                with lock:
                    state.risk_scores[asset_id] = score

    finally:
        consumer.close()
