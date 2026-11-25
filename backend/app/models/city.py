"""Core Pydantic models and simulation state schemas for Parallel World."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TileType(str, Enum):
    EMPTY = "empty"
    WATER = "water"
    ROAD = "road"
    RESIDENTIAL = "residential"
    HOSPITAL = "hospital"
    SCHOOL = "school"
    INDUSTRY = "industry"
    POWER_STATION = "power_station"
    SHELTER = "shelter"
    PARK = "park"


class DisasterType(str, Enum):
    FLOOD = "flood"
    TRAFFIC = "traffic"
    POWER_FAILURE = "power_failure"
    FIRE = "fire"
    EARTHQUAKE = "earthquake"
    ROAD_BLOCKAGE = "road_blockage"


class VehicleKind(str, Enum):
    COMMUTER = "commuter"
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    EVAC_BUS = "evac_bus"


class TileState(BaseModel):
    x: int
    y: int
    tile_type: TileType = TileType.EMPTY
    elevation: float = 1.0  # 0.0 (riverbed) to 5.0 (high ground)
    population: int = 0
    capacity: int = 0
    occupied: int = 0
    health: float = 100.0  # 0 - 100 structural/operational health
    powered: bool = True
    power_load_mw: float = 0.0
    power_supply_mw: float = 0.0
    flood_depth: float = 0.0  # 0.0 - 1.0
    fire_intensity: float = 0.0  # 0.0 - 1.0
    road_blocked: bool = False
    congestion: float = 0.0  # 0.0 - 1.0
    queue_length: int = 0
    signal_phase: Literal["NS", "EW"] = "NS"
    rerouted: bool = False


class VehicleAgent(BaseModel):
    id: str
    kind: VehicleKind
    x: float
    y: float
    target_x: int
    target_y: int
    path: list[tuple[int, int]] = Field(default_factory=list)
    status: Literal["moving", "queued", "rerouting", "arrived", "responding"] = "moving"
    algorithm_used: Literal["A*", "Dijkstra"] = "A*"


class EmergencyIncident(BaseModel):
    id: str
    x: int
    y: int
    kind: str
    severity: float
    citizens_at_risk: int
    priority_rank: int = 0
    assigned_unit: str | None = None
    resolved: bool = False


class EvacuationRoute(BaseModel):
    origin: tuple[int, int]
    shelter: tuple[int, int]
    path: list[tuple[int, int]]
    cost: float
    citizens: int


class PowerLink(BaseModel):
    source: tuple[int, int]
    target: tuple[int, int]
    powered: bool
    load_ratio: float


class DisasterConfig(BaseModel):
    flood: bool = False
    traffic: bool = False
    power_failure: bool = False
    fire: bool = False
    earthquake: bool = False
    road_blockage: bool = False
    intensity: int = Field(default=65, ge=0, le=100)


class InterventionState(BaseModel):
    emergency_response_active: bool = False
    alternative_routes_active: bool = False
    load_shedding_active: bool = False


class CityMetrics(BaseModel):
    tick: int = 0
    sim_time_minutes: float = 0.0
    city_stability: float = 100.0
    citizens_affected: int = 0
    total_population: int = 0
    services_active: float = 100.0
    blocked_roads: int = 0
    power_coverage: float = 100.0
    evacuated_citizens: int = 0
    recovery_hours: float = 0.0
    avg_congestion: float = 0.0
    active_fires: int = 0
    flooded_tiles: int = 0
    overloaded_stations: int = 0


class CSMetrics(BaseModel):
    graph_nodes: int = 0
    graph_edges: int = 0
    dijkstra_routes_computed: int = 0
    dijkstra_avg_cost: float = 0.0
    astar_paths_computed: int = 0
    astar_nodes_expanded: int = 0
    bfs_power_components: int = 0
    dfs_critical_reachable: int = 0
    priority_queue_size: int = 0
    top_priority_incident: str = "None"
    traffic_queue_total: int = 0
    undo_stack_depth: int = 0
    ca_flood_cells: int = 0
    ca_fire_cells: int = 0
    multi_agent_count: int = 0
    simpy_events_processed: int = 0
    simpy_sim_time: float = 0.0
    ml_predicted_stability_next: float = 100.0
    ml_predicted_recovery_hours: float = 0.0
    sqlite_saved_snapshots: int = 0


class UniverseSnapshot(BaseModel):
    universe_id: str
    label: str
    strategy_description: str
    city_name: str
    width: int
    height: int
    tick: int
    running: bool
    disasters: DisasterConfig
    interventions: InterventionState
    metrics: CityMetrics
    cs_metrics: CSMetrics
    tiles: list[TileState]
    vehicles: list[VehicleAgent]
    incidents: list[EmergencyIncident]
    evacuation_routes: list[EvacuationRoute]
    power_links: list[PowerLink]
    history_curve: list[dict[str, float | int]] = Field(default_factory=list)
    event_log: list[str] = Field(default_factory=list)


class ParallelComparison(BaseModel):
    tick: int
    running: bool
    universe_a: UniverseSnapshot
    universe_b: UniverseSnapshot
    delta_stability: float
    delta_citizens_affected: int
    delta_blocked_roads: int
    delta_recovery_hours: float


class TileEditRequest(BaseModel):
    x: int
    y: int
    tile_type: TileType | None = None
    toggle_block_road: bool = False
    ignite_fire: bool = False
    trigger_flood: bool = False


class DisasterUpdateRequest(BaseModel):
    flood: bool | None = None
    traffic: bool | None = None
    power_failure: bool | None = None
    fire: bool | None = None
    earthquake: bool | None = None
    road_blockage: bool | None = None
    intensity: int | None = Field(default=None, ge=0, le=100)


class InterventionRequest(BaseModel):
    universe_id: str = "primary"
    action: Literal[
        "deploy_emergency_response",
        "toggle_emergency_response",
        "activate_alternative_routes",
        "toggle_alternative_routes",
        "toggle_load_shedding",
        "clear_road_blockages",
        "reset",
    ]


class AIAdviceRequest(BaseModel):
    universe_id: str = "primary"
    question: str | None = None


class AIRecommendation(BaseModel):
    id: str
    title: str
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    action_key: str | None = None
    rationale: str
    projected_stability_gain: float
    projected_citizens_saved: int
    tradeoff: str


class AIAdviceResponse(BaseModel):
    summary: str
    source: Literal["deterministic-engine", "ollama+engine"]
    ollama_model: str | None = None
    recommendations: list[AIRecommendation]
    answer: str | None = None


class CityPresetInfo(BaseModel):
    id: str
    name: str
    description: str
    width: int
    height: int
    population: int
    is_custom: bool = False


class SaveCityRequest(BaseModel):
    name: str
    description: str = "Custom designed city"
    universe_id: str = "primary"


class TimelineSummary(BaseModel):
    universe_id: str
    current_tick: int
    stack_depth: int
    available_ticks: list[int]
    can_undo: bool
    latest_events: list[str] = Field(default_factory=list)


class RewindRequest(BaseModel):
    universe_id: str = "primary"
    target_tick: int | None = None
    steps: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
