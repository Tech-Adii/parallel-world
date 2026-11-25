"""Main CitySimulation orchestrator and ParallelWorldManager (Universe A vs Universe B)."""

from __future__ import annotations

import copy
import random
from typing import Literal

from app.db.storage import SimulationDatabase
from app.engine.disasters import DisasterEngine
from app.engine.evacuation import EvacuationDispatchEngine
from app.engine.graph_router import Coord, RoadNetworkRouter
from app.engine.ml_predictor import TrafficAndRecoveryPredictor
from app.engine.power_grid import PowerGridSimulator
from app.engine.presets import get_preset_blueprint, make_tile
from app.engine.time_machine import SimulationFrame, TimeMachineStack
from app.models.city import (
    CSMetrics,
    CityMetrics,
    DisasterConfig,
    DisasterUpdateRequest,
    EmergencyIncident,
    EvacuationRoute,
    InterventionState,
    ParallelComparison,
    PowerLink,
    TileEditRequest,
    TileState,
    TileType,
    UniverseSnapshot,
    VehicleAgent,
    VehicleKind,
)


class CitySimulation:
    """Self-contained simulation universe orchestrating graph routing, CA disasters, power grid, and Time Machine."""

    def __init__(
        self,
        universe_id: str,
        label: str,
        strategy_description: str,
        blueprint: dict,
        db: SimulationDatabase,
        seed: int = 42,
        initial_disasters: DisasterConfig | None = None,
        initial_interventions: InterventionState | None = None,
    ) -> None:
        self.universe_id = universe_id
        self.label = label
        self.strategy_description = strategy_description
        self.db = db
        self.seed = seed
        self.rng = random.Random(seed)

        self.city_name: str = blueprint["name"]
        self.preset_id: str = blueprint["id"]
        self.width: int = int(blueprint["width"])
        self.height: int = int(blueprint["height"])
        self._initial_blueprint = copy.deepcopy(blueprint)

        self.tile_map: dict[Coord, TileState] = {
            (t.x, t.y): copy.deepcopy(t) for t in blueprint["tiles"]
        }
        self.tick: int = 0
        self.running: bool = True
        self.evacuated_citizens: int = 0

        self.disasters = copy.deepcopy(initial_disasters) if initial_disasters else DisasterConfig(
            flood=True,
            traffic=True,
            power_failure=False,
            fire=False,
            intensity=65,
        )
        self.interventions = (
            copy.deepcopy(initial_interventions) if initial_interventions else InterventionState()
        )

        self.router = RoadNetworkRouter(self.width, self.height)
        self.power_grid = PowerGridSimulator()
        self.disaster_engine = DisasterEngine(self.width, self.height, seed=seed)
        self.evac_engine = EvacuationDispatchEngine()
        self.ml_predictor = TrafficAndRecoveryPredictor()
        self.time_machine = TimeMachineStack()

        self.vehicles: list[VehicleAgent] = []
        self.incidents: list[EmergencyIncident] = []
        self.evacuation_routes: list[EvacuationRoute] = []
        self.power_links: list[PowerLink] = []
        self.history_curve: list[dict[str, float | int]] = []
        self.event_log: list[str] = [f"Initialized {self.city_name} ({self.label})."]
        self.sqlite_snapshots: int = self.db.snapshot_count()

        self._ca_flood_cells = 0
        self._ca_fire_cells = 0
        self._power_coverage = 100.0
        self._total_queued = 0

        # Build initial graph, power, vehicles, and push frame 0
        self._bootstrap()

    def _bootstrap(self) -> None:
        self.router.rebuild_graph(self.tile_map, self.interventions.alternative_routes_active)
        self._power_coverage, self.power_links, _ = self.power_grid.step(
            self.tile_map,
            self.disasters.power_failure,
            self.disasters.intensity,
            self.interventions.load_shedding_active,
        )
        self._spawn_vehicles(target_count=18)
        self._recompute_metrics(record_history=True)
        self._push_time_machine_frame()

    def reset(self, blueprint: dict | None = None, keep_disasters: bool = True) -> None:
        bp = copy.deepcopy(blueprint) if blueprint else copy.deepcopy(self._initial_blueprint)
        self._initial_blueprint = copy.deepcopy(bp)
        self.city_name = bp["name"]
        self.preset_id = bp["id"]
        self.width = int(bp["width"])
        self.height = int(bp["height"])
        self.tile_map = {(t.x, t.y): copy.deepcopy(t) for t in bp["tiles"]}
        self.tick = 0
        self.evacuated_citizens = 0
        self.rng = random.Random(self.seed)
        if not keep_disasters:
            self.disasters = DisasterConfig(intensity=65)
            self.interventions = InterventionState()
        self.router = RoadNetworkRouter(self.width, self.height)
        self.power_grid = PowerGridSimulator()
        self.disaster_engine = DisasterEngine(self.width, self.height, seed=self.seed)
        self.evac_engine = EvacuationDispatchEngine()
        self.time_machine.clear()
        self.vehicles.clear()
        self.incidents.clear()
        self.evacuation_routes.clear()
        self.history_curve.clear()
        self.event_log = [f"Reset {self.city_name} ({self.label}) to tick 0."]
        self._bootstrap()

    def _spawn_vehicles(self, target_count: int) -> None:
        road_nodes = list(self.router.graph.nodes())
        if len(road_nodes) < 2:
            return
        while len(self.vehicles) < target_count:
            start = self.rng.choice(road_nodes)
            goal = self.rng.choice(road_nodes)
            if start == goal:
                continue
            path = self.router.astar_path(start, goal)
            if len(path) < 2:
                continue
            kind = VehicleKind.COMMUTER
            if self.interventions.emergency_response_active and len(self.vehicles) % 5 == 0:
                kind = VehicleKind.AMBULANCE if len(self.vehicles) % 10 == 0 else VehicleKind.FIRE_TRUCK
            vid = f"V-{self.tick}-{len(self.vehicles)}-{self.rng.randint(100,999)}"
            self.vehicles.append(
                VehicleAgent(
                    id=vid,
                    kind=kind,
                    x=float(start[0]),
                    y=float(start[1]),
                    target_x=goal[0],
                    target_y=goal[1],
                    path=path[1:],
                    status="responding" if kind != VehicleKind.COMMUTER else "moving",
                    algorithm_used="A*",
                )
            )

    def _step_vehicles(self) -> None:
        road_nodes = list(self.router.graph.nodes())
        for t in self.tile_map.values():
            if t.tile_type == TileType.ROAD:
                t.congestion = max(0.0, round(t.congestion * 0.72, 2))
                t.rerouted = False

        # Surge vehicle count during traffic congestion disaster
        desired = 22
        if self.disasters.traffic:
            desired = 22 + int((self.disasters.intensity / 100.0) * 20)
        if self.interventions.emergency_response_active:
            desired += 6

        if len(self.vehicles) < desired:
            self._spawn_vehicles(desired)
        elif len(self.vehicles) > desired:
            self.vehicles = self.vehicles[:desired]

        # Ensure emergency vehicles exist when emergency response is active
        if self.interventions.emergency_response_active and self.incidents:
            has_responder = any(v.kind != VehicleKind.COMMUTER for v in self.vehicles)
            if not has_responder and road_nodes:
                inc = self.incidents[0]
                goal_road = self.router.nearest_road((inc.x, inc.y), self.tile_map)
                if goal_road:
                    start = self.rng.choice(road_nodes)
                    path = self.router.astar_path(start, goal_road)
                    if path:
                        self.vehicles.append(
                            VehicleAgent(
                                id=f"AMB-{self.tick}",
                                kind=VehicleKind.AMBULANCE,
                                x=float(start[0]),
                                y=float(start[1]),
                                target_x=goal_road[0],
                                target_y=goal_road[1],
                                path=path[1:],
                                status="responding",
                                algorithm_used="A*",
                            )
                        )

        surviving: list[VehicleAgent] = []
        for v in self.vehicles:
            curr_coord = (int(round(v.x)), int(round(v.y)))
            curr_tile = self.tile_map.get(curr_coord)

            # Congestion accumulation on occupied road
            if curr_tile and curr_tile.tile_type == TileType.ROAD:
                inc_amt = 0.28 if self.disasters.traffic else 0.14
                if self.interventions.alternative_routes_active:
                    inc_amt *= 0.6
                curr_tile.congestion = min(1.0, round(curr_tile.congestion + inc_amt, 2))

            if not v.path:
                # Reached destination -> pick new trip
                if len(road_nodes) >= 2:
                    goal = self.rng.choice(road_nodes)
                    if v.kind in (VehicleKind.AMBULANCE, VehicleKind.FIRE_TRUCK) and self.incidents:
                        inc = self.rng.choice(self.incidents[:3])
                        inc_road = self.router.nearest_road((inc.x, inc.y), self.tile_map)
                        if inc_road:
                            goal = inc_road
                    new_path = self.router.astar_path(curr_coord, goal) if curr_coord in self.router.graph else []
                    if len(new_path) > 1:
                        v.target_x, v.target_y = goal
                        v.path = new_path[1:]
                        v.status = "responding" if v.kind != VehicleKind.COMMUTER else "moving"
                        surviving.append(v)
                continue

            next_step = v.path[0]
            next_tile = self.tile_map.get(next_step)
            if not next_tile or next_tile.road_blocked or (curr_coord, next_step) not in self.router.graph.edges():
                # Obstacle encountered! Reroute with A* if alternative routes enabled or emergency unit
                if self.interventions.alternative_routes_active or v.kind != VehicleKind.COMMUTER:
                    if curr_coord in self.router.graph:
                        reroute = self.router.astar_path(curr_coord, (v.target_x, v.target_y))
                        if len(reroute) > 1:
                            v.path = reroute[1:]
                            v.status = "rerouting"
                            if curr_tile:
                                curr_tile.rerouted = True
                            surviving.append(v)
                            continue
                # Otherwise enqueue vehicle into intersection FIFO queue
                q = self.router.intersection_queues.get(curr_coord)
                if q is not None and v.id not in q and len(q) < 12:
                    q.append(v.id)
                v.status = "queued"
                surviving.append(v)
                continue

            # Check queue congestion slowdown
            if next_tile.congestion > 0.78 and not self.interventions.alternative_routes_active:
                q = self.router.intersection_queues.get(next_step)
                if q is not None and len(q) < 10 and self.rng.random() < 0.5:
                    q.append(v.id)
                    v.status = "queued"
                    surviving.append(v)
                    continue

            # Advance along path
            v.x = float(next_step[0])
            v.y = float(next_step[1])
            v.path.pop(0)
            v.status = "responding" if v.kind != VehicleKind.COMMUTER else "moving"
            if self.interventions.alternative_routes_active and next_tile:
                next_tile.rerouted = True
            surviving.append(v)

        self.vehicles = surviving
        self._total_queued = self.router.update_traffic_queues(
            self.tile_map,
            self.tick,
            self.interventions.alternative_routes_active,
            self._power_coverage,
        )

    def step(self) -> None:
        """Advance simulation by 1 tick across all 7 engines."""
        self.tick += 1
        new_events: list[str] = []

        # 1. Disaster Cellular Automata + SimPy discrete-event advance
        self._ca_flood_cells, self._ca_fire_cells, dis_events = self.disaster_engine.step(
            self.tile_map,
            self.disasters,
            self.interventions.emergency_response_active,
            self.tick,
        )
        new_events.extend(dis_events)

        # 2. Power Grid BFS/DFS & Cascade simulation
        self._power_coverage, self.power_links, pwr_events = self.power_grid.step(
            self.tile_map,
            self.disasters.power_failure,
            self.disasters.intensity,
            self.interventions.load_shedding_active,
        )
        new_events.extend(pwr_events)

        # 3. Rebuild NetworkX road network & simulate multi-agent traffic + A* + Queues
        self.router.rebuild_graph(self.tile_map, self.interventions.alternative_routes_active)
        self._step_vehicles()

        # 4. Priority-Queue Emergency Dispatch + Dijkstra Shelter Evacuation
        self.incidents, self.evacuation_routes, newly_evacuated, evac_events = (
            self.evac_engine.evaluate_and_dispatch(
                self.tile_map,
                self.router,
                self.interventions.emergency_response_active,
                self.tick,
            )
        )
        self.evacuated_citizens += newly_evacuated
        new_events.extend(evac_events)

        # Keep concise rolling event log
        for ev in new_events[:4]:
            self.event_log.append(f"[T{self.tick:03d}] {ev}")
        self.event_log = self.event_log[-18:]

        # 5. Recompute KPIs + NumPy ML recovery/stability forecast
        metrics, _ = self._recompute_metrics(record_history=True)

        # 6. Push Time Machine stack frame & periodically checkpoint to SQLite
        self._push_time_machine_frame()
        if self.tick % 5 == 0:
            self.sqlite_snapshots = self.db.record_snapshot(
                universe_id=self.universe_id,
                city_name=self.city_name,
                tick=self.tick,
                stability=metrics.city_stability,
                citizens_affected=metrics.citizens_affected,
                blocked_roads=metrics.blocked_roads,
                summary_payload={"services_active": metrics.services_active, "power": metrics.power_coverage},
            )

    def _recompute_metrics(self, record_history: bool = False) -> tuple[CityMetrics, CSMetrics]:
        tiles = list(self.tile_map.values())
        roads = [t for t in tiles if t.tile_type == TileType.ROAD]
        buildings = [
            t
            for t in tiles
            if t.tile_type
            in (TileType.RESIDENTIAL, TileType.HOSPITAL, TileType.SCHOOL, TileType.INDUSTRY, TileType.POWER_STATION, TileType.SHELTER)
        ]

        total_pop = sum(t.population for t in tiles) + self.evacuated_citizens
        blocked_roads = sum(1 for r in roads if r.road_blocked)
        avg_congestion = round((sum(r.congestion for r in roads) / max(1, len(roads))) * 100.0, 1)
        avg_health = sum(b.health for b in buildings) / max(1, len(buildings))

        citizens_affected = 0
        for b in buildings:
            hazard = b.flood_depth * 0.8 + b.fire_intensity * 1.1 + (0.35 if not b.powered else 0.0)
            health_hit = max(0.0, (100.0 - b.health) / 100.0)
            impact_ratio = min(1.0, hazard * 0.75 + health_hit * 0.65)
            if impact_ratio > 0.12:
                citizens_affected += int(b.population * impact_ratio)

        # Add traffic/stranded commuters contribution when congestion or blockages are high
        if self.disasters.traffic or blocked_roads > 0:
            road_disruption = (blocked_roads / max(1, len(roads))) * 0.25 + (avg_congestion / 100.0) * 0.15
            citizens_affected += int(total_pop * road_disruption * 0.45)

        citizens_affected = min(total_pop, citizens_affected)

        # Services active: hospitals + schools + shelters + power coverage
        service_tiles = [t for t in tiles if t.tile_type in (TileType.HOSPITAL, TileType.SCHOOL, TileType.SHELTER)]
        if service_tiles:
            svc_scores = [
                (t.health / 100.0) * (1.0 if t.powered else 0.45) * max(0.2, 1.0 - t.flood_depth - t.fire_intensity)
                for t in service_tiles
            ]
            services_active = round((sum(svc_scores) / len(svc_scores)) * 100.0, 1)
        else:
            services_active = round(self._power_coverage, 1)

        road_open_pct = 100.0 * (1.0 - (blocked_roads / max(1, len(roads))))
        affected_pct = 100.0 * (citizens_affected / max(1, total_pop))
        stability_raw = (
            avg_health * 0.32
            + services_active * 0.24
            + self._power_coverage * 0.20
            + road_open_pct * 0.14
            + max(0.0, 100.0 - affected_pct * 1.35) * 0.10
        )
        if self.interventions.emergency_response_active:
            stability_raw = min(100.0, stability_raw + 6.5)
        if self.interventions.alternative_routes_active:
            stability_raw = min(100.0, stability_raw + 3.5)

        city_stability = round(max(5.0, min(100.0, stability_raw)), 1)

        metrics = CityMetrics(
            tick=self.tick,
            sim_time_minutes=round(self.disaster_engine.simpy_env.now, 1),
            city_stability=city_stability,
            citizens_affected=citizens_affected,
            total_population=total_pop,
            services_active=services_active,
            blocked_roads=blocked_roads,
            power_coverage=self._power_coverage,
            evacuated_citizens=self.evacuated_citizens,
            recovery_hours=0.0,
            avg_congestion=avg_congestion,
            active_fires=self._ca_fire_cells,
            flooded_tiles=self._ca_flood_cells,
            overloaded_stations=self.power_grid.overloaded_stations,
        )

        pred_stability, recovery_hours = self.ml_predictor.predict(
            self.history_curve, metrics, self.interventions
        )
        metrics.recovery_hours = recovery_hours

        if record_history:
            self.history_curve.append(
                {
                    "tick": self.tick,
                    "stability": city_stability,
                    "affected": citizens_affected,
                    "services": services_active,
                    "blocked_roads": blocked_roads,
                }
            )
            self.history_curve = self.history_curve[-80:]

        cs_metrics = CSMetrics(
            graph_nodes=self.router.graph.number_of_nodes(),
            graph_edges=self.router.graph.number_of_edges(),
            dijkstra_routes_computed=self.router.dijkstra_routes_computed,
            dijkstra_avg_cost=self.router.dijkstra_avg_cost,
            astar_paths_computed=self.router.astar_paths_computed,
            astar_nodes_expanded=self.router.astar_nodes_expanded,
            bfs_power_components=self.power_grid.bfs_components,
            dfs_critical_reachable=self.power_grid.dfs_critical_reachable,
            priority_queue_size=self.evac_engine.priority_queue_size,
            top_priority_incident=self.evac_engine.top_priority_incident,
            traffic_queue_total=self._total_queued,
            undo_stack_depth=self.time_machine.depth(),
            ca_flood_cells=self._ca_flood_cells,
            ca_fire_cells=self._ca_fire_cells,
            multi_agent_count=len(self.vehicles),
            simpy_events_processed=self.disaster_engine.simpy_events_processed,
            simpy_sim_time=round(self.disaster_engine.simpy_env.now, 1),
            ml_predicted_stability_next=pred_stability,
            ml_predicted_recovery_hours=recovery_hours,
            sqlite_saved_snapshots=self.sqlite_snapshots,
        )
        return metrics, cs_metrics

    def _push_time_machine_frame(self) -> None:
        frame = SimulationFrame(
            tick=self.tick,
            sim_time_minutes=float(self.disaster_engine.simpy_env.now),
            tiles=list(self.tile_map.values()),
            vehicles=self.vehicles,
            disasters=self.disasters,
            interventions=self.interventions,
            evacuated_citizens=self.evacuated_citizens,
            history_curve=self.history_curve,
            event_log=self.event_log,
        )
        self.time_machine.push(frame)

    def rewind(self, target_tick: int | None = None, steps: int = 1) -> bool:
        """Rewind simulation using Time Machine LIFO Stack."""
        if target_tick is not None:
            frame = self.time_machine.rewind_to_tick(target_tick)
        else:
            frame = self.time_machine.pop_steps(steps)
        if not frame:
            return False

        self.tick = frame.tick
        self.tile_map = {(t.x, t.y): copy.deepcopy(t) for t in frame.tiles}
        self.vehicles = copy.deepcopy(frame.vehicles)
        self.disasters = copy.deepcopy(frame.disasters)
        self.interventions = copy.deepcopy(frame.interventions)
        self.evacuated_citizens = frame.evacuated_citizens
        self.history_curve = copy.deepcopy(frame.history_curve)
        self.event_log = copy.deepcopy(frame.event_log) + [f"[REWIND] Returned to tick {self.tick}."]
        self.router.rebuild_graph(self.tile_map, self.interventions.alternative_routes_active)
        self._power_coverage, self.power_links, _ = self.power_grid.step(
            self.tile_map,
            self.disasters.power_failure,
            self.disasters.intensity,
            self.interventions.load_shedding_active,
        )
        self.incidents, self.evacuation_routes, _, _ = self.evac_engine.evaluate_and_dispatch(
            self.tile_map, self.router, self.interventions.emergency_response_active, self.tick
        )
        return True

    def edit_tile(self, req: TileEditRequest) -> bool:
        coord = (req.x, req.y)
        tile = self.tile_map.get(coord)
        if not tile:
            return False
        if req.tile_type is not None:
            elev = 0.0 if req.tile_type == TileType.WATER else max(1.0, tile.elevation)
            self.tile_map[coord] = make_tile(req.x, req.y, req.tile_type, elev)
            self.event_log.append(f"[BUILD] Placed {req.tile_type.value} at ({req.x},{req.y}).")
        if req.toggle_block_road and self.tile_map[coord].tile_type == TileType.ROAD:
            self.tile_map[coord].road_blocked = not self.tile_map[coord].road_blocked
            state_lbl = "blocked" if self.tile_map[coord].road_blocked else "cleared"
            self.event_log.append(f"[ROAD] Road ({req.x},{req.y}) manually {state_lbl}.")
        if req.ignite_fire and self.tile_map[coord].tile_type != TileType.WATER:
            self.tile_map[coord].fire_intensity = 0.85
            self.disasters.fire = True
            self.event_log.append(f"[HAZARD] Fire ignited at ({req.x},{req.y}).")
        if req.trigger_flood:
            self.tile_map[coord].flood_depth = 0.85
            self.disasters.flood = True
            self.event_log.append(f"[HAZARD] Localized flood at ({req.x},{req.y}).")

        self.router.rebuild_graph(self.tile_map, self.interventions.alternative_routes_active)
        self._power_coverage, self.power_links, _ = self.power_grid.step(
            self.tile_map,
            self.disasters.power_failure,
            self.disasters.intensity,
            self.interventions.load_shedding_active,
        )
        return True

    def apply_action(self, action: str) -> None:
        if action == "deploy_emergency_response":
            self.interventions.emergency_response_active = True
            self.event_log.append(f"[T{self.tick:03d}] Emergency response teams deployed.")
        elif action == "toggle_emergency_response":
            self.interventions.emergency_response_active = not self.interventions.emergency_response_active
            state = "deployed" if self.interventions.emergency_response_active else "stood down"
            self.event_log.append(f"[T{self.tick:03d}] Emergency response {state}.")
        elif action == "activate_alternative_routes":
            self.interventions.alternative_routes_active = True
            self.event_log.append(f"[T{self.tick:03d}] Dynamic A* alternative routes activated.")
        elif action == "toggle_alternative_routes":
            self.interventions.alternative_routes_active = not self.interventions.alternative_routes_active
            state = "enabled" if self.interventions.alternative_routes_active else "disabled"
            self.event_log.append(f"[T{self.tick:03d}] Alternative A* routing {state}.")
        elif action == "toggle_load_shedding":
            self.interventions.load_shedding_active = not self.interventions.load_shedding_active
            state = "enabled" if self.interventions.load_shedding_active else "disabled"
            self.event_log.append(f"[T{self.tick:03d}] Smart power load shedding {state}.")
        elif action == "clear_road_blockages":
            cleared = 0
            for t in self.tile_map.values():
                if t.tile_type == TileType.ROAD and t.road_blocked and t.flood_depth < 0.7:
                    t.road_blocked = False
                    cleared += 1
            self.router.rebuild_graph(self.tile_map, self.interventions.alternative_routes_active)
            self.event_log.append(f"[T{self.tick:03d}] Cleared {cleared} blocked road segment(s).")
        elif action == "reset":
            self.reset()

    def update_disasters(self, req: DisasterUpdateRequest) -> None:
        for field_name in ("flood", "traffic", "power_failure", "fire", "earthquake", "road_blockage", "intensity"):
            val = getattr(req, field_name)
            if val is not None:
                setattr(self.disasters, field_name, val)

    def snapshot(self) -> UniverseSnapshot:
        metrics, cs_metrics = self._recompute_metrics(record_history=False)
        ordered_tiles = [self.tile_map[(x, y)] for y in range(self.height) for x in range(self.width)]
        return UniverseSnapshot(
            universe_id=self.universe_id,
            label=self.label,
            strategy_description=self.strategy_description,
            city_name=self.city_name,
            width=self.width,
            height=self.height,
            tick=self.tick,
            running=self.running,
            disasters=copy.deepcopy(self.disasters),
            interventions=copy.deepcopy(self.interventions),
            metrics=metrics,
            cs_metrics=cs_metrics,
            tiles=copy.deepcopy(ordered_tiles),
            vehicles=copy.deepcopy(self.vehicles),
            incidents=copy.deepcopy(self.incidents),
            evacuation_routes=copy.deepcopy(self.evacuation_routes),
            power_links=copy.deepcopy(self.power_links),
            history_curve=list(self.history_curve),
            event_log=list(self.event_log),
        )


class ParallelWorldManager:
    """Coordinates primary city simulation and synchronized Parallel Universes (Universe A vs Universe B)."""

    def __init__(self, db: SimulationDatabase | None = None) -> None:
        self.db = db or SimulationDatabase()
        default_bp = get_preset_blueprint("metro_harbor")
        default_disasters = DisasterConfig(
            flood=True,
            traffic=True,
            power_failure=True,
            fire=False,
            earthquake=False,
            road_blockage=True,
            intensity=65,
        )

        self.primary = CitySimulation(
            universe_id="primary",
            label="Command Center",
            strategy_description="Interactive primary city twin controlled directly by the administrator.",
            blueprint=default_bp,
            db=self.db,
            seed=101,
            initial_disasters=default_disasters,
            initial_interventions=InterventionState(),
        )

        self.universe_a = CitySimulation(
            universe_id="universe_a",
            label="Universe A",
            strategy_description="No emergency intervention (baseline disaster propagation)",
            blueprint=default_bp,
            db=self.db,
            seed=2026,
            initial_disasters=default_disasters,
            initial_interventions=InterventionState(
                emergency_response_active=False,
                alternative_routes_active=False,
                load_shedding_active=False,
            ),
        )

        self.universe_b = CitySimulation(
            universe_id="universe_b",
            label="Universe B",
            strategy_description="Optimized emergency response (dispatch + A* reroute + load shedding)",
            blueprint=default_bp,
            db=self.db,
            seed=2026,
            initial_disasters=default_disasters,
            initial_interventions=InterventionState(
                emergency_response_active=True,
                alternative_routes_active=True,
                load_shedding_active=True,
            ),
        )

        # Pre-warm 6 ticks so the initial UI immediately presents rich live city telemetry!
        for _ in range(6):
            self.step_all()

    def get_universe(self, universe_id: str) -> CitySimulation:
        if universe_id == "universe_a":
            return self.universe_a
        if universe_id == "universe_b":
            return self.universe_b
        return self.primary

    def step_all(self) -> None:
        if self.primary.running:
            self.primary.step()
        if self.universe_a.running and self.universe_b.running:
            self.universe_a.step()
            self.universe_b.step()

    def set_running(self, running: bool, scope: Literal["all", "primary", "parallel"] = "all") -> None:
        if scope in ("all", "primary"):
            self.primary.running = running
        if scope in ("all", "parallel"):
            self.universe_a.running = running
            self.universe_b.running = running

    def load_city_blueprint(self, blueprint_id: str) -> bool:
        bp = self.db.load_custom_city(blueprint_id) or get_preset_blueprint(blueprint_id)
        self.primary.reset(blueprint=bp, keep_disasters=True)
        self.universe_a.reset(blueprint=bp, keep_disasters=True)
        self.universe_b.reset(blueprint=bp, keep_disasters=True)
        # Re-establish default comparison interventions for A vs B
        self.universe_a.interventions = InterventionState(False, False, False)
        self.universe_b.interventions = InterventionState(True, True, True)
        return True

    def sync_parallel_from_primary(self) -> None:
        """Clone current primary city layout & disasters into Universe A and B for controlled A/B comparison."""
        tiles_copy = [copy.deepcopy(t) for t in self.primary.tile_map.values()]
        bp = {
            "id": self.primary.preset_id,
            "name": self.primary.city_name,
            "description": "Synchronized twin from Command Center",
            "width": self.primary.width,
            "height": self.primary.height,
            "tiles": tiles_copy,
        }
        dis = copy.deepcopy(self.primary.disasters)
        self.universe_a.disasters = copy.deepcopy(dis)
        self.universe_b.disasters = copy.deepcopy(dis)
        self.universe_a.reset(blueprint=bp, keep_disasters=True)
        self.universe_b.reset(blueprint=bp, keep_disasters=True)
        self.universe_a.interventions = InterventionState(False, False, False)
        self.universe_b.interventions = InterventionState(True, True, True)

    def update_parallel_disasters(self, req: DisasterUpdateRequest) -> None:
        self.universe_a.update_disasters(req)
        self.universe_b.update_disasters(req)

    def reset_parallel(self) -> None:
        self.universe_a.reset(keep_disasters=True)
        self.universe_b.reset(keep_disasters=True)
        self.universe_a.interventions = InterventionState(False, False, False)
        self.universe_b.interventions = InterventionState(True, True, True)

    def parallel_comparison(self) -> ParallelComparison:
        snap_a = self.universe_a.snapshot()
        snap_b = self.universe_b.snapshot()
        return ParallelComparison(
            tick=snap_a.tick,
            running=self.universe_a.running and self.universe_b.running,
            universe_a=snap_a,
            universe_b=snap_b,
            delta_stability=round(snap_b.metrics.city_stability - snap_a.metrics.city_stability, 1),
            delta_citizens_affected=snap_a.metrics.citizens_affected - snap_b.metrics.citizens_affected,
            delta_blocked_roads=snap_a.metrics.blocked_roads - snap_b.metrics.blocked_roads,
            delta_recovery_hours=round(snap_a.metrics.recovery_hours - snap_b.metrics.recovery_hours, 1),
        )
