"""Graph algorithms for road networks: NetworkX graph, A* vehicle navigation, Dijkstra evacuation, and FIFO intersection queues."""

from __future__ import annotations

import heapq
import math
from collections import deque

import networkx as nx

from app.models.city import EvacuationRoute, TileState, TileType


Coord = tuple[int, int]


class RoadNetworkRouter:
    """Manages road graph topology, traffic queues, A* routing, and Dijkstra evacuation paths."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.graph: nx.Graph = nx.Graph()
        self.intersection_queues: dict[Coord, deque[str]] = {}
        self.dijkstra_routes_computed: int = 0
        self.dijkstra_avg_cost: float = 0.0
        self.astar_paths_computed: int = 0
        self.astar_nodes_expanded: int = 0

    def rebuild_graph(self, tile_map: dict[Coord, TileState], alternative_routes: bool) -> None:
        """Construct weighted NetworkX graph from current road tiles."""
        self.graph.clear()
        road_coords = [coord for coord, tile in tile_map.items() if tile.tile_type == TileType.ROAD]

        for coord in road_coords:
            self.graph.add_node(coord)
            if coord not in self.intersection_queues:
                self.intersection_queues[coord] = deque()

        # Remove queues for deleted road tiles
        for old_coord in list(self.intersection_queues.keys()):
            if old_coord not in tile_map or tile_map[old_coord].tile_type != TileType.ROAD:
                del self.intersection_queues[old_coord]

        for x, y in road_coords:
            t1 = tile_map[(x, y)]
            for dx, dy in ((1, 0), (0, 1)):
                nb = (x + dx, y + dy)
                if nb in tile_map and tile_map[nb].tile_type == TileType.ROAD:
                    t2 = tile_map[nb]
                    if t1.road_blocked or t2.road_blocked:
                        continue
                    weight = self._edge_weight(t1, t2, alternative_routes)
                    self.graph.add_edge((x, y), nb, weight=weight)

    @staticmethod
    def _edge_weight(t1: TileState, t2: TileState, alternative_routes: bool) -> float:
        """Edge traversal cost incorporating congestion, flood water, fire proximity, and queue length."""
        avg_congestion = 0.5 * (t1.congestion + t2.congestion)
        avg_flood = 0.5 * (t1.flood_depth + t2.flood_depth)
        avg_fire = 0.5 * (t1.fire_intensity + t2.fire_intensity)
        avg_queue = 0.5 * (t1.queue_length + t2.queue_length)

        if alternative_routes:
            # Intelligent route optimization penalizes congestion, flood, and queues heavily to divert traffic
            return 1.0 + avg_congestion * 7.5 + avg_flood * 14.0 + avg_fire * 18.0 + avg_queue * 1.4
        # Unoptimized baseline: drivers mostly ignore mild congestion until gridlock occurs
        return 1.0 + avg_congestion * 1.2 + avg_flood * 3.0 + avg_fire * 4.0

    def nearest_road(self, coord: Coord, tile_map: dict[Coord, TileState]) -> Coord | None:
        """Find nearest unblocked road tile adjacent or close to a building using BFS."""
        if coord in self.graph:
            return coord
        visited = {coord}
        q: deque[tuple[Coord, int]] = deque([(coord, 0)])
        while q:
            (cx, cy), dist = q.popleft()
            if dist > 4:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx_c = (cx + dx, cy + dy)
                if not (0 <= nx_c[0] < self.width and 0 <= nx_c[1] < self.height):
                    continue
                if nx_c in visited:
                    continue
                visited.add(nx_c)
                if nx_c in self.graph:
                    return nx_c
                t = tile_map.get(nx_c)
                if t and t.tile_type != TileType.WATER:
                    q.append((nx_c, dist + 1))
        return None

    def astar_path(self, start: Coord, goal: Coord) -> list[Coord]:
        """Explicit A* search with Manhattan heuristic for intelligent vehicle navigation."""
        if start not in self.graph or goal not in self.graph:
            return []
        if start == goal:
            return [start]

        def heuristic(a: Coord, b: Coord) -> float:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_heap: list[tuple[float, float, Coord]] = [(heuristic(start, goal), 0.0, start)]
        came_from: dict[Coord, Coord] = {}
        g_score: dict[Coord, float] = {start: 0.0}
        closed: set[Coord] = set()
        expanded = 0

        while open_heap:
            _, current_g, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            expanded += 1

            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                self.astar_paths_computed += 1
                self.astar_nodes_expanded += expanded
                return path

            for neighbor in self.graph.neighbors(current):
                if neighbor in closed:
                    continue
                edge_cost = float(self.graph[current][neighbor]["weight"])
                tentative_g = current_g + edge_cost
                if tentative_g < g_score.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_heap, (f, tentative_g, neighbor))

        self.astar_nodes_expanded += expanded
        return []

    def dijkstra_evacuation_routes(
        self,
        tile_map: dict[Coord, TileState],
        affected_origins: list[tuple[Coord, int]],
        shelters: list[TileState],
    ) -> list[EvacuationRoute]:
        """Use Dijkstra's algorithm to compute shortest safe evacuation paths to available shelters."""
        routes: list[EvacuationRoute] = []
        shelter_access: list[tuple[Coord, TileState]] = []
        for s in shelters:
            if s.fire_intensity > 0.45 or s.flood_depth > 0.55 or s.health <= 15.0:
                continue
            if s.occupied >= s.capacity:
                continue
            road_node = self.nearest_road((s.x, s.y), tile_map)
            if road_node is not None:
                shelter_access.append((road_node, s))

        if not shelter_access or not affected_origins:
            self.dijkstra_routes_computed = 0
            self.dijkstra_avg_cost = 0.0
            return []

        costs: list[float] = []
        for origin_building, citizens in affected_origins:
            start_road = self.nearest_road(origin_building, tile_map)
            if start_road is None or start_road not in self.graph:
                continue
            try:
                lengths, paths = nx.single_source_dijkstra(self.graph, start_road, weight="weight")
            except nx.NetworkXError:
                continue

            best_cost = math.inf
            best_path: list[Coord] = []
            best_shelter: Coord | None = None
            for shelter_road, shelter_tile in shelter_access:
                if shelter_road in lengths:
                    # Slight load-balancing penalty if shelter is nearly full
                    fill_penalty = (shelter_tile.occupied / max(1, shelter_tile.capacity)) * 4.0
                    total_cost = float(lengths[shelter_road]) + fill_penalty
                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_path = list(paths[shelter_road])
                        best_shelter = (shelter_tile.x, shelter_tile.y)

            if best_shelter is not None and best_path:
                routes.append(
                    EvacuationRoute(
                        origin=origin_building,
                        shelter=best_shelter,
                        path=best_path,
                        cost=round(best_cost, 2),
                        citizens=citizens,
                    )
                )
                costs.append(best_cost)

        self.dijkstra_routes_computed = len(routes)
        self.dijkstra_avg_cost = round(sum(costs) / len(costs), 2) if costs else 0.0
        return routes

    def update_traffic_queues(
        self,
        tile_map: dict[Coord, TileState],
        tick: int,
        alternative_routes: bool,
        power_coverage: float,
    ) -> int:
        """Advance intersection signals and drain FIFO queues per road node."""
        total_queued = 0
        # Reset queue lengths on tiles first
        for coord, q in self.intersection_queues.items():
            tile = tile_map.get(coord)
            if not tile or tile.tile_type != TileType.ROAD:
                continue

            if tile.road_blocked:
                tile.queue_length = len(q)
                total_queued += len(q)
                continue

            # Signal switching every 3 ticks (or adaptive based on queue buildup if alternative_routes active)
            if alternative_routes:
                # Adaptive traffic signal optimization drains faster when powered
                drain = 3 if tile.powered else 2
                if tick % 2 == 0:
                    tile.signal_phase = "EW" if tile.signal_phase == "NS" else "NS"
            else:
                drain = 2 if (tile.powered and power_coverage > 40) else 1
                if tick % 4 == 0:
                    tile.signal_phase = "EW" if tile.signal_phase == "NS" else "NS"

            for _ in range(min(drain, len(q))):
                q.popleft()

            tile.queue_length = len(q)
            total_queued += len(q)
        return total_queued
