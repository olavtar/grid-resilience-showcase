# This project was developed with assistance from AI tools.

"""Event emission logic for each scenario beat."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from confluent_kafka import Producer

from grid_common.events import (
    CameraEscalate,
    CustomerImpact,
    FaultEvent,
    FaultType,
    GridCell,
    OpsEvent,
    RestorationEvent,
    Severity,
    SwitchAction,
    WeatherAlert,
    WeatherForecast,
    WorkOrder,
    WorkOrderPriority,
)
from grid_common.kafka import publish_event

logger = structlog.get_logger()


def _build_forecast_grid_cells(hour: int) -> list[GridCell]:
    """Build grid cells with progressive storm intensity."""
    intensity = min(hour / 18.0, 1.0)
    cells = []
    for lat in [36.06, 36.08, 36.10, 36.12]:
        for lon in [-79.50, -79.47, -79.44]:
            north_factor = (lat - 36.04) / 0.08
            wind = 5.0 + 20.0 * intensity * north_factor
            precip = 2.0 + 15.0 * intensity * north_factor
            freezing = intensity > 0.3 and lat >= 36.08
            cells.append(
                GridCell(
                    lat=lat,
                    lon=lon,
                    t2m_k=275.0 - 8.0 * intensity * north_factor,
                    u10m_mps=wind * 0.7,
                    v10m_mps=wind * 0.3,
                    tp_mm=precip,
                    cfrzr=freezing,
                    crain=not freezing,
                    cicep=False,
                    csnow=False,
                )
            )
    return cells


def emit_forecast_events(producer: Producer, config: dict[str, Any], trace_id: str) -> int:
    """Emit weather forecast and alert events for the forecast beat."""
    count = 0
    now = datetime.now(tz=UTC)

    for hour in [0, 6, 12, 18]:
        forecast = WeatherForecast(
            forecast_hour=hour,
            valid_time=now,
            grid_cells=_build_forecast_grid_cells(hour),
            trace_id=trace_id,
            source_service="scenario-engine",
        )
        publish_event(producer, "grid.weather.forecast", forecast)
        count += 1

    alert = WeatherAlert(
        alert_type="freezing_rain",
        severity=Severity.WARNING,
        message="Freezing rain expected in Piedmont NC corridor within 18 hours. "
        "Ice accumulation 6-12mm forecast on northern sections.",
        affected_area_lat_min=config.get("lat_min", 36.05),
        affected_area_lat_max=config.get("lat_max", 36.12),
        affected_area_lon_min=config.get("lon_min", -79.55),
        affected_area_lon_max=config.get("lon_max", -79.40),
        forecast_hour=0,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.weather.alerts", alert)

    ops = OpsEvent(
        category="weather",
        title="Earth-2 forecast published",
        detail="CorrDiff 3km downscaled forecast for Piedmont NC corridor. "
        "Freezing rain onset in 18 hours.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()
    return count + 2


def emit_escalate_events(producer: Producer, config: dict[str, Any], trace_id: str) -> int:
    """Emit camera escalation events for priority assets."""
    camera_ids = config.get(
        "escalate_cameras",
        [
            "CAM-P037",
            "CAM-P052",
            "CAM-P063",
            "CAM-SUB-A",
            "CAM-P041",
        ],
    )
    escalate = CameraEscalate(
        camera_ids=camera_ids,
        reason="Risk engine flagged priority assets — escalating monitoring frequency",
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.cameras.escalate", escalate)

    ops = OpsEvent(
        category="camera",
        title="Monitoring escalated",
        detail=f"Camera analysis frequency increased on {len(camera_ids)} priority cameras.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()
    return 2


def emit_dispatch_work_orders(producer: Producer, trace_id: str) -> int:
    """Emit work orders for defects found during camera inspection."""
    count = 0

    work_orders = [
        WorkOrder(
            asset_id="P-037",
            title="Cracked crossarm repair",
            description="Cracked crossarm detected by AI camera inspection. "
            "Immediate replacement recommended before ice loading.",
            priority=WorkOrderPriority.HIGH,
            required_skills=["lineman", "bucket_truck"],
            lat=36.0753,
            lon=-79.4167,
            estimated_duration_minutes=120,
            trace_id=trace_id,
            source_service="scenario-engine",
        ),
        WorkOrder(
            asset_id="P-052",
            title="Vegetation clearance",
            description="Vegetation encroachment detected within 1.5m of conductor. "
            "Clearance required before storm arrival.",
            priority=WorkOrderPriority.HIGH,
            required_skills=["lineman", "vegetation"],
            lat=36.0573,
            lon=-79.398,
            estimated_duration_minutes=90,
            trace_id=trace_id,
            source_service="scenario-engine",
        ),
        WorkOrder(
            asset_id="P-063",
            title="Ice accumulation removal",
            description="Ice accumulation detected on conductor spans. "
            "De-icing required to prevent line failure.",
            priority=WorkOrderPriority.CRITICAL,
            required_skills=["lineman", "hot_work"],
            lat=36.1076,
            lon=-79.514,
            estimated_duration_minutes=60,
            trace_id=trace_id,
            source_service="scenario-engine",
        ),
    ]

    for wo in work_orders:
        publish_event(producer, "grid.crew.work-orders", wo)
        count += 1

    ops = OpsEvent(
        category="dispatch",
        title="Work orders created from AI findings",
        detail=f"{len(work_orders)} work orders generated from camera defect detections.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops)
    count += 1

    producer.flush()
    return count


DOWNSTREAM_ASSETS = [
    "P-038",
    "P-039",
    "P-040",
    "T-004",
    "P-041",
    "P-042",
    "P-043",
    "P-044",
    "P-045",
    "P-046",
    "SW-004",
    "P-047",
    "P-048",
    "P-049",
    "P-050",
    "T-005",
    "P-051",
    "P-052",
    "P-053",
    "P-054",
    "P-055",
]

RESTORED_BY_SWITCH = [
    "P-038",
    "P-039",
    "P-040",
    "T-004",
    "P-041",
    "P-042",
    "P-043",
    "P-044",
    "P-045",
    "P-046",
    "SW-004",
]


def emit_storm_fault(producer: Producer, config: dict[str, Any], trace_id: str) -> int:
    """Beat: Storm — fault occurs, downstream assets lose power."""
    fault_config = config.get("fault", {})
    feeder_id = fault_config.get("feeder_id", "F-12")
    affected_customers = fault_config.get("affected_customers", 847)

    fault = FaultEvent(
        feeder_id=feeder_id,
        segment_id="SEG-037",
        fault_type=FaultType.ICE_LOADING,
        affected_customers=affected_customers,
        affected_asset_ids=DOWNSTREAM_ASSETS,
        lat=36.0753,
        lon=-79.4167,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.faults.detected", fault, key=feeder_id)

    impact = CustomerImpact(
        fault_id=fault.fault_id,
        feeder_id=feeder_id,
        total_affected=affected_customers,
        remaining=affected_customers,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.customer.impact", impact, key=feeder_id)

    ops = OpsEvent(
        category="fault",
        title=f"Fault on {feeder_id} at P-037",
        detail=f"Ice loading failure. {affected_customers} customers affected. "
        f"{len(DOWNSTREAM_ASSETS)} downstream assets without power.",
        severity=Severity.CRITICAL,
        related_asset_id="P-037",
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()
    return 3


def emit_storm_restore(producer: Producer, config: dict[str, Any], trace_id: str) -> int:
    """Beat: Restore — automatic switching restores partial service."""
    fault_config = config.get("fault", {})
    feeder_id = fault_config.get("feeder_id", "F-12")
    affected_customers = fault_config.get("affected_customers", 847)
    customers_restored = fault_config.get("customers_restored", 312)
    switch_id = fault_config.get("switch_id", "TS-04")

    restoration = RestorationEvent(
        fault_id="",
        switch_id=switch_id,
        action=SwitchAction.CLOSE,
        customers_restored=customers_restored,
        remaining_affected=affected_customers - customers_restored,
        etr_minutes=135,
        restored_asset_ids=RESTORED_BY_SWITCH,
        adms_capacity_check="Receiving feeder capacity check: 4.2 MW available / "
        "3.1 MW transfer load — CLEAR. Tie switch close command authorized.",
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.faults.restoration", restoration, key=feeder_id)

    impact = CustomerImpact(
        fault_id="",
        feeder_id=feeder_id,
        total_affected=affected_customers,
        restored=customers_restored,
        remaining=affected_customers - customers_restored,
        etr_minutes=135,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.customer.impact", impact, key=feeder_id)

    ops = OpsEvent(
        category="restoration",
        title=f"Automatic switching — {customers_restored} customers restored",
        detail=f"{switch_id} closed. {affected_customers - customers_restored} remaining. "
        "ETR: 2h 15m.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()
    return 3
