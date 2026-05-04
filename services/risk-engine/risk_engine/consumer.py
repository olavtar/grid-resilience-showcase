# This project was developed with assistance from AI tools.

"""Kafka consumer loop — consumes weather forecasts and recomputes risk scores."""

from __future__ import annotations

import json
import threading
from typing import Any

import psycopg
import structlog
from confluent_kafka import Producer

from grid_common.events import AssetRiskScore, GridCell, OpsEvent, Severity
from grid_common.kafka import create_consumer, publish_event
from risk_engine.scoring import compute_asset_risk
from risk_engine.settings import RiskEngineSettings

logger = structlog.get_logger()


def _load_assets(dsn: str) -> list[dict[str, Any]]:
    """Load all assets from PostgreSQL."""
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, asset_type, subtype, lat, lon, install_year, "
                "expected_lifespan_years, feeder_id, is_end_of_line, "
                "vegetation_clearance_m, last_inspection_date, status, "
                "customers_downstream "
                "FROM assets WHERE status = 'in_service'"
            )
            cols = [desc[0] for desc in (cur.description or [])]
            return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


def consumer_loop(
    settings: RiskEngineSettings,
    producer: Producer,
    risk_scores: dict[str, AssetRiskScore],
    lock: threading.Lock,
) -> None:
    """Consume weather forecasts and recompute all asset risk scores."""
    consumer = create_consumer(
        settings,
        group_id="risk-engine",
        topics=["grid.weather.forecast"],
        auto_offset_reset="earliest",
    )

    assets = _load_assets(settings.dsn)
    logger.info("assets_loaded", count=len(assets))

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning("consumer_error", error=str(msg.error()))
                continue

            try:
                raw = msg.value()
                if raw is None:
                    continue
                data = json.loads(raw.decode())
                grid_cells = [GridCell(**c) for c in data.get("grid_cells", [])]
                forecast_hour = data.get("forecast_hour", 0)
                trace_id = data.get("trace_id")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("forecast_parse_error", error=str(e))
                continue

            scored: list[AssetRiskScore] = []
            for asset in assets:
                score = compute_asset_risk(asset, grid_cells, forecast_hour, settings)
                score.trace_id = trace_id
                scored.append(score)
                publish_event(producer, "grid.assets.risk-scores", score, key=asset["id"])

            with lock:
                for s in scored:
                    risk_scores[s.asset_id] = s

            top = max(scored, key=lambda s: s.composite_score) if scored else None
            if forecast_hour < 18:
                producer.flush()
                logger.info("risk_scores_computed", count=len(scored), hour=forecast_hour)
                continue
            ops = OpsEvent(
                category="risk",
                title=f"Risk scores computed for {len(scored)} assets",
                detail=f"Forecast hour {forecast_hour}. "
                f"Top risk: {top.asset_id} at {top.composite_score:.2f}"
                if top
                else "No assets scored",
                severity=Severity.INFO,
                trace_id=trace_id,
                source_service="risk-engine",
            )
            publish_event(producer, "grid.ops.events", ops)
            producer.flush()

            logger.info(
                "risk_scores_computed",
                count=len(scored),
                top_asset=top.asset_id if top else None,
                top_score=top.composite_score if top else None,
            )
    finally:
        consumer.close()
