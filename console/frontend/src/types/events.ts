// This project was developed with assistance from AI tools.

export interface GridEvent {
  event_id: string;
  timestamp: string;
  trace_id?: string;
  source_service?: string;
}

export interface AssetRiskScore extends GridEvent {
  asset_id: string;
  asset_type: string;
  composite_score: number;
  breakdown: {
    weather_exposure: number;
    age: number;
    vegetation: number;
    inspection_recency: number;
  };
  forecast_hour: number;
}

export interface InspectionFinding extends GridEvent {
  camera_id: string;
  asset_id: string;
  frame_event_id: string;
  findings: DefectFinding[];
  model: string;
  inference_latency_ms?: number;
  image_data?: string;
}

export interface DefectFinding {
  defect_type: string;
  severity: "info" | "warning" | "major" | "critical";
  confidence: number;
  description: string;
  recommended_action: string;
}

export interface DispatchAssignment extends GridEvent {
  plan_id: string;
  crew_id: string;
  work_order_id: string;
  status: string;
  route_polyline: number[][];
  eta_minutes?: number;
  cuopt_solve_time_ms?: number;
  guardrails_result?: string;
  guardrails_message?: string;
  dispatcher_justification?: string;
}

export interface FaultEvent extends GridEvent {
  fault_id: string;
  feeder_id: string;
  segment_id: string;
  fault_type: string;
  affected_customers: number;
  lat: number;
  lon: number;
}

export interface CustomerImpact extends GridEvent {
  fault_id: string;
  feeder_id: string;
  total_affected: number;
  restored: number;
  remaining: number;
  etr_minutes?: number;
}

export interface OpsEvent extends GridEvent {
  category: string;
  title: string;
  detail: string;
  severity: string;
  related_asset_id?: string;
}

export interface ScenarioState {
  scenario_id?: string;
  scenario_name?: string;
  current_beat: string;
  is_running: boolean;
  storm_triggered: boolean;
  fault_triggered: boolean;
  events_emitted: number;
}

export interface TopologyData {
  feeders: Array<{ id: string; substation_id: string; name: string; status: string }>;
  assets: Array<{
    id: string;
    asset_type: string;
    subtype: string;
    lat: number;
    lon: number;
    feeder_id: string;
    status: string;
    customers_downstream: number;
  }>;
  segments: Array<{
    id: string;
    feeder_id: string;
    from_asset_id: string;
    to_asset_id: string;
    status: string;
    customers_served: number;
  }>;
  cameras: Array<{
    id: string;
    lat: number;
    lon: number;
    camera_type: string;
    asset_id: string;
    status: string;
  }>;
}
