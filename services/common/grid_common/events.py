# This project was developed with assistance from AI tools.

"""Pydantic event schemas for all Kafka topics in the grid resilience platform."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def _event_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    MAJOR = "major"
    CRITICAL = "critical"


class WorkOrderPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkOrderStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DispatchStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_TRANSIT = "in_transit"
    ON_SITE = "on_site"
    COMPLETED = "completed"


class CrewStatus(StrEnum):
    AVAILABLE = "available"
    EN_ROUTE = "en_route"
    ON_SITE = "on_site"
    OFF_SHIFT = "off_shift"


class FaultType(StrEnum):
    LINE_DOWN = "line_down"
    EQUIPMENT_FAILURE = "equipment_failure"
    VEGETATION_CONTACT = "vegetation_contact"
    ANIMAL_CONTACT = "animal_contact"
    ICE_LOADING = "ice_loading"
    UNKNOWN = "unknown"


class SwitchAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------


class GridEvent(BaseModel):
    """Base for all grid events."""

    event_id: str = Field(default_factory=_event_id)
    timestamp: datetime = Field(default_factory=_now)
    trace_id: str | None = None
    source_service: str | None = None


# ---------------------------------------------------------------------------
# Weather (grid.weather.forecast, grid.weather.alerts)
# ---------------------------------------------------------------------------


class GridCell(BaseModel):
    """Single grid cell from the Earth-2 forecast."""

    lat: float
    lon: float
    t2m_k: float = Field(description="2m temperature in Kelvin")
    u10m_mps: float = Field(description="10m U-wind component in m/s")
    v10m_mps: float = Field(description="10m V-wind component in m/s")
    tp_mm: float = Field(description="Total precipitation in mm")
    crain: bool = Field(default=False, description="Categorical rain flag")
    cfrzr: bool = Field(default=False, description="Categorical freezing rain flag")
    cicep: bool = Field(default=False, description="Categorical ice pellets flag")
    csnow: bool = Field(default=False, description="Categorical snow flag")


class WeatherForecast(GridEvent):
    """Earth-2 CorrDiff downscaled weather forecast for the corridor."""

    forecast_hour: int = Field(description="Hours from T0")
    valid_time: datetime
    grid_cells: list[GridCell]
    resolution_km: float = 3.0
    model: str = "corrdiff"


class WeatherAlert(GridEvent):
    """Threshold-based weather alert derived from forecast."""

    alert_type: str = Field(description="e.g. freezing_rain, high_wind, ice_accumulation")
    severity: Severity
    message: str
    affected_area_lat_min: float
    affected_area_lat_max: float
    affected_area_lon_min: float
    affected_area_lon_max: float
    forecast_hour: int


# ---------------------------------------------------------------------------
# Risk (grid.assets.risk-scores)
# ---------------------------------------------------------------------------


class RiskBreakdown(BaseModel):
    """Explainable sub-scores for the composite risk score."""

    weather_exposure: float = Field(ge=0.0, le=1.0)
    age: float = Field(ge=0.0, le=1.0)
    vegetation: float = Field(ge=0.0, le=1.0)
    inspection_recency: float = Field(ge=0.0, le=1.0)


class AssetRiskScore(GridEvent):
    """Per-asset risk score with explainable breakdown."""

    asset_id: str
    asset_type: str
    composite_score: float = Field(ge=0.0, le=1.0)
    breakdown: RiskBreakdown
    forecast_hour: int


# ---------------------------------------------------------------------------
# Camera (grid.cameras.frames, grid.cameras.findings, grid.cameras.escalate)
# ---------------------------------------------------------------------------


class InspectionFrame(GridEvent):
    """Camera frame published for AI analysis."""

    camera_id: str
    asset_id: str
    image_url: str = Field(description="URL or path to the camera frame image")
    frame_sequence: int = 0
    escalated: bool = False


class DefectFinding(BaseModel):
    """Single defect found in a camera frame."""

    defect_type: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    recommended_action: str


class InspectionFinding(GridEvent):
    """AI-detected findings from camera frame analysis."""

    camera_id: str
    asset_id: str
    frame_event_id: str = Field(description="event_id of the InspectionFrame that was analyzed")
    findings: list[DefectFinding]
    model: str = "cosmos-reason-2-8b"
    inference_latency_ms: float | None = None
    image_data: str | None = Field(
        default=None, description="Base64-encoded image, included when findings are present"
    )


class CameraEscalate(GridEvent):
    """Request to escalate monitoring frequency on specific cameras."""

    camera_ids: list[str]
    reason: str = ""


# ---------------------------------------------------------------------------
# Work Orders (grid.crew.work-orders)
# ---------------------------------------------------------------------------


class WorkOrder(GridEvent):
    """Work order generated from findings or fault response."""

    work_order_id: str = Field(default_factory=_event_id)
    asset_id: str
    title: str
    description: str
    priority: WorkOrderPriority
    required_skills: list[str] = Field(default_factory=list)
    status: WorkOrderStatus = WorkOrderStatus.OPEN
    finding_event_id: str | None = None
    fault_event_id: str | None = None
    estimated_duration_minutes: int = 60
    lat: float
    lon: float


# ---------------------------------------------------------------------------
# Dispatch (grid.crew.dispatch)
# ---------------------------------------------------------------------------


class DispatchAssignment(GridEvent):
    """Crew dispatch assignment from cuOpt optimization."""

    plan_id: str
    crew_id: str
    work_order_id: str
    status: DispatchStatus = DispatchStatus.PENDING_APPROVAL
    route_polyline: list[list[float]] = Field(
        default_factory=list, description="[[lat, lon], ...] route points"
    )
    eta_minutes: float | None = None
    cuopt_solve_time_ms: float | None = None
    guardrails_result: str | None = Field(
        default=None, description="pass, warn, or block from NeMo Guardrails"
    )
    guardrails_message: str | None = None
    dispatcher_justification: str | None = None


# ---------------------------------------------------------------------------
# Faults (grid.faults.detected, grid.faults.restoration)
# ---------------------------------------------------------------------------


class FaultEvent(GridEvent):
    """Fault detected on the distribution grid."""

    fault_id: str = Field(default_factory=_event_id)
    feeder_id: str
    segment_id: str
    fault_type: FaultType
    affected_customers: int = 0
    lat: float
    lon: float


class RestorationEvent(GridEvent):
    """Switching or restoration action on the grid."""

    fault_id: str
    switch_id: str | None = None
    action: SwitchAction | None = None
    customers_restored: int = 0
    remaining_affected: int = 0
    etr_minutes: int | None = None
    adms_capacity_check: str | None = Field(
        default=None, description="Capacity verification summary"
    )


# ---------------------------------------------------------------------------
# Crew Telemetry (grid.crew.telemetry)
# ---------------------------------------------------------------------------


class CrewTelemetry(GridEvent):
    """Real-time crew location and status update."""

    crew_id: str
    lat: float
    lon: float
    status: CrewStatus
    current_work_order_id: str | None = None
    speed_kmh: float | None = None
    heading_degrees: float | None = None


# ---------------------------------------------------------------------------
# Ops Events (grid.ops.events)
# ---------------------------------------------------------------------------


class OpsEvent(GridEvent):
    """Lifecycle event from any service for the event stream."""

    category: str = Field(description="weather, risk, camera, dispatch, fault, restoration, system")
    title: str
    detail: str = ""
    severity: Severity = Severity.INFO
    related_asset_id: str | None = None


# ---------------------------------------------------------------------------
# Customer Impact (grid.customer.impact)
# ---------------------------------------------------------------------------


class CustomerImpact(GridEvent):
    """Customer outage impact summary."""

    fault_id: str
    feeder_id: str
    total_affected: int
    restored: int = 0
    remaining: int = 0
    etr_minutes: int | None = None
    ami_confirmations: int = 0


# ---------------------------------------------------------------------------
# AMI Outages (grid.ami.outages)
# ---------------------------------------------------------------------------


class AmiOutage(GridEvent):
    """Simulated AMI last-gasp outage confirmation."""

    meter_id: str
    asset_id: str
    segment_id: str
    feeder_id: str
    outage_confirmed: bool = True
