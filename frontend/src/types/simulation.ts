export type TileType =
  | "empty"
  | "water"
  | "road"
  | "residential"
  | "hospital"
  | "school"
  | "industry"
  | "power_station"
  | "shelter"
  | "park";

export interface TileState {
  x: number;
  y: number;
  tile_type: TileType;
  elevation: number;
  population: number;
  capacity: number;
  occupied: number;
  health: number;
  powered: boolean;
  power_load_mw: number;
  power_supply_mw: number;
  flood_depth: number;
  fire_intensity: number;
  road_blocked: boolean;
  congestion: number;
  queue_length: number;
  signal_phase: "NS" | "EW";
  rerouted: boolean;
}

export interface VehicleAgent {
  id: string;
  kind: "commuter" | "ambulance" | "fire_truck" | "evac_bus";
  x: number;
  y: number;
  target_x: number;
  target_y: number;
  path: [number, number][];
  status: "moving" | "queued" | "rerouting" | "arrived" | "responding";
  algorithm_used: "A*" | "Dijkstra";
}

export interface EmergencyIncident {
  id: string;
  x: number;
  y: number;
  kind: string;
  severity: number;
  citizens_at_risk: number;
  priority_rank: number;
  assigned_unit: string | null;
  resolved: boolean;
}

export interface EvacuationRoute {
  origin: [number, number];
  shelter: [number, number];
  path: [number, number][];
  cost: number;
  citizens: number;
}

export interface PowerLink {
  source: [number, number];
  target: [number, number];
  powered: boolean;
  load_ratio: number;
}

export interface DisasterConfig {
  flood: boolean;
  traffic: boolean;
  power_failure: boolean;
  fire: boolean;
  earthquake: boolean;
  road_blockage: boolean;
  intensity: number;
}

export interface InterventionState {
  emergency_response_active: boolean;
  alternative_routes_active: boolean;
  load_shedding_active: boolean;
}

export interface CityMetrics {
  tick: number;
  sim_time_minutes: number;
  city_stability: number;
  citizens_affected: number;
  total_population: number;
  services_active: number;
  blocked_roads: number;
  power_coverage: number;
  evacuated_citizens: number;
  recovery_hours: number;
  avg_congestion: number;
  active_fires: number;
  flooded_tiles: number;
  overloaded_stations: number;
}

export interface CSMetrics {
  graph_nodes: number;
  graph_edges: number;
  dijkstra_routes_computed: number;
  dijkstra_avg_cost: number;
  astar_paths_computed: number;
  astar_nodes_expanded: number;
  bfs_power_components: number;
  dfs_critical_reachable: number;
  priority_queue_size: number;
  top_priority_incident: string;
  traffic_queue_total: number;
  undo_stack_depth: number;
  ca_flood_cells: number;
  ca_fire_cells: number;
  multi_agent_count: number;
  simpy_events_processed: number;
  simpy_sim_time: number;
  ml_predicted_stability_next: number;
  ml_predicted_recovery_hours: number;
  sqlite_saved_snapshots: number;
}

export interface HistoryPoint {
  tick: number;
  stability: number;
  affected: number;
  services: number;
  blocked_roads: number;
}

export interface UniverseSnapshot {
  universe_id: string;
  label: string;
  strategy_description: string;
  city_name: string;
  width: number;
  height: number;
  tick: number;
  running: boolean;
  disasters: DisasterConfig;
  interventions: InterventionState;
  metrics: CityMetrics;
  cs_metrics: CSMetrics;
  tiles: TileState[];
  vehicles: VehicleAgent[];
  incidents: EmergencyIncident[];
  evacuation_routes: EvacuationRoute[];
  power_links: PowerLink[];
  history_curve: HistoryPoint[];
  event_log: string[];
}

export interface ParallelComparison {
  tick: number;
  running: boolean;
  universe_a: UniverseSnapshot;
  universe_b: UniverseSnapshot;
  delta_stability: number;
  delta_citizens_affected: number;
  delta_blocked_roads: number;
  delta_recovery_hours: number;
}

export interface CityPresetInfo {
  id: string;
  name: string;
  description: string;
  width: number;
  height: number;
  population: number;
  is_custom: boolean;
}

export interface AIRecommendation {
  id: string;
  title: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  action_key: string | null;
  rationale: string;
  projected_stability_gain: number;
  projected_citizens_saved: number;
  tradeoff: string;
}

export interface AIAdviceResponse {
  summary: string;
  source: "deterministic-engine" | "ollama+engine";
  ollama_model: string | null;
  recommendations: AIRecommendation[];
  answer: string | null;
}

export interface TimelineSummary {
  universe_id: string;
  current_tick: number;
  stack_depth: number;
  available_ticks: number[];
  can_undo: boolean;
  latest_events: string[];
}

export interface FullStateBundle {
  speed: number;
  primary: UniverseSnapshot;
  parallel: ParallelComparison;
  cities: CityPresetInfo[];
}

export type AppViewMode = "command" | "parallel" | "builder" | "analytics";
export type MapOverlayMode = "standard" | "power" | "evacuation" | "congestion";
export type BuilderTool = TileType | "block_road" | "ignite_fire" | "trigger_flood" | "inspect";
