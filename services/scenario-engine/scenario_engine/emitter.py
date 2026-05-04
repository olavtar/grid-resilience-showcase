# This project was developed with assistance from AI tools.

"""Event emission logic for each scenario beat."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from confluent_kafka import Producer

from grid_common.events import (
    AmiOutage,
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


def emit_storm_events(producer: Producer, config: dict[str, Any], trace_id: str) -> int:
    """Emit intensified weather alerts for storm arrival."""
    alert = WeatherAlert(
        alert_type="ice_accumulation",
        severity=Severity.CRITICAL,
        message="Ice accumulation exceeding 12mm on northern corridor. "
        "Peak loading on conductors and crossarms.",
        affected_area_lat_min=config.get("lat_min", 36.05),
        affected_area_lat_max=config.get("lat_max", 36.12),
        affected_area_lon_min=config.get("lon_min", -79.55),
        affected_area_lon_max=config.get("lon_max", -79.40),
        forecast_hour=18,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.weather.alerts", alert)

    impact = CustomerImpact(
        fault_id="",
        feeder_id="",
        total_affected=0,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.customer.impact", impact)

    ops = OpsEvent(
        category="weather",
        title="Storm arrived",
        detail="Ice storm peak conditions active. Monitoring 12,400 customers on affected feeders.",
        severity=Severity.CRITICAL,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops)
    producer.flush()
    return 3


def emit_fault_events(producer: Producer, config: dict[str, Any], trace_id: str) -> int:
    """Emit fault, AMI outage, and restoration events."""
    count = 0

    fault_config = config.get("fault", {})
    feeder_id = fault_config.get("feeder_id", "F-12")
    segment_id = fault_config.get("segment_id", "SEG-052")
    affected_customers = fault_config.get("affected_customers", 847)
    fault_lat = fault_config.get("lat", 36.088)
    fault_lon = fault_config.get("lon", -79.465)

    fault = FaultEvent(
        feeder_id=feeder_id,
        segment_id=segment_id,
        fault_type=FaultType.ICE_LOADING,
        affected_customers=affected_customers,
        lat=fault_lat,
        lon=fault_lon,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.faults.detected", fault, key=feeder_id)
    count += 1

    ops_fault = OpsEvent(
        category="fault",
        title=f"Fault detected on {feeder_id}",
        detail=f"Segment {segment_id}: {affected_customers} customers affected.",
        severity=Severity.CRITICAL,
        related_asset_id=segment_id,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops_fault)
    count += 1

    ami_meters = fault_config.get("ami_meters", 20)
    for i in range(ami_meters):
        ami = AmiOutage(
            meter_id=f"MTR-{segment_id}-{i:04d}",
            asset_id=f"P-{51 + (i % 2):03d}",
            segment_id=segment_id,
            feeder_id=feeder_id,
            trace_id=trace_id,
            source_service="scenario-engine",
        )
        publish_event(producer, "grid.ami.outages", ami, key=feeder_id)
        count += 1

    impact = CustomerImpact(
        fault_id=fault.fault_id,
        feeder_id=feeder_id,
        total_affected=affected_customers,
        remaining=affected_customers,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.customer.impact", impact, key=feeder_id)
    count += 1

    switch_id = fault_config.get("switch_id", "TS-04")
    customers_restored = fault_config.get("customers_restored", 312)
    restoration = RestorationEvent(
        fault_id=fault.fault_id,
        switch_id=switch_id,
        action=SwitchAction.CLOSE,
        customers_restored=customers_restored,
        remaining_affected=affected_customers - customers_restored,
        etr_minutes=135,
        adms_capacity_check="Receiving feeder capacity check: 4.2 MW available / "
        "3.1 MW transfer load — CLEAR. Tie switch close command authorized.",
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.faults.restoration", restoration, key=feeder_id)
    count += 1

    impact_updated = CustomerImpact(
        fault_id=fault.fault_id,
        feeder_id=feeder_id,
        total_affected=affected_customers,
        restored=customers_restored,
        remaining=affected_customers - customers_restored,
        etr_minutes=135,
        ami_confirmations=ami_meters,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.customer.impact", impact_updated, key=feeder_id)
    count += 1

    wo_investigate = WorkOrder(
        asset_id=segment_id,
        title="Fault investigation — ice loading damage",
        description=f"Investigate fault on {feeder_id} segment {segment_id}. "
        "Suspected ice loading damage to conductor or crossarm.",
        priority=WorkOrderPriority.CRITICAL,
        required_skills=["lineman"],
        lat=fault_lat,
        lon=fault_lon,
        fault_event_id=fault.fault_id,
        estimated_duration_minutes=90,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.crew.work-orders", wo_investigate)
    count += 1

    wo_repair = WorkOrder(
        asset_id=segment_id,
        title="Line repair — restore faulted segment",
        description=f"Repair and restore {feeder_id} segment {segment_id}. "
        f"{affected_customers - customers_restored} customers remaining without power.",
        priority=WorkOrderPriority.CRITICAL,
        required_skills=["lineman", "bucket_truck"],
        lat=fault_lat + 0.001,
        lon=fault_lon + 0.001,
        fault_event_id=fault.fault_id,
        estimated_duration_minutes=120,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.crew.work-orders", wo_repair)
    count += 1

    ops_restore = OpsEvent(
        category="restoration",
        title=f"Automatic switching — {customers_restored} customers restored",
        detail=f"{switch_id} closed. {affected_customers - customers_restored} remaining. "
        "ETR: 2h 15m.",
        severity=Severity.INFO,
        trace_id=trace_id,
        source_service="scenario-engine",
    )
    publish_event(producer, "grid.ops.events", ops_restore)
    count += 1

    producer.flush()
    return count
