"""Power Grid Simulator: BFS/DFS connectivity, overload redistribution, and cascading blackouts."""

from __future__ import annotations

from collections import deque

from app.models.city import PowerLink, TileState, TileType


Coord = tuple[int, int]

POWER_CONSUMING_TYPES = {
    TileType.HOSPITAL,
    TileType.SHELTER,
    TileType.SCHOOL,
    TileType.RESIDENTIAL,
    TileType.INDUSTRY,
    TileType.ROAD,
}

CRITICAL_TYPES = {TileType.HOSPITAL, TileType.SHELTER}


class PowerGridSimulator:
    """Simulates power distribution, BFS connected components, DFS reachability, and cascading trips."""

    def __init__(self) -> None:
        self.bfs_components: int = 0
        self.dfs_critical_reachable: int = 0
        self.overloaded_stations: int = 0

    def step(
        self,
        tile_map: dict[Coord, TileState],
        power_failure_active: bool,
        intensity: int,
        load_shedding_active: bool,
    ) -> tuple[float, list[PowerLink], list[str]]:
        """Evaluate grid supply vs demand, run BFS/DFS connectivity, and model cascading trips."""
        events: list[str] = []
        stations = [t for t in tile_map.values() if t.tile_type == TileType.POWER_STATION]
        consumers = [t for t in tile_map.values() if t.tile_type in POWER_CONSUMING_TYPES]

        # Reset powered flags initially
        for t in tile_map.values():
            t.powered = False

        if not stations:
            self.bfs_components = 0
            self.dfs_critical_reachable = 0
            self.overloaded_stations = 0
            return 0.0, [], ["Grid alert: No active power stations remain in the city."]

        # Compute effective output of each power station
        effective_capacity: dict[Coord, float] = {}
        active_stations: list[TileState] = []
        for st in stations:
            damage_factor = max(0.0, st.health / 100.0)
            flood_penalty = max(0.0, 1.0 - st.flood_depth * 1.3)
            fire_penalty = max(0.0, 1.0 - st.fire_intensity * 1.4)
            fault_penalty = 1.0
            if power_failure_active:
                # Primary substation takes severe fault hit proportional to intensity
                fault_penalty = max(0.22, 1.0 - (intensity / 100.0) * 0.72)
            cap = st.power_supply_mw * damage_factor * flood_penalty * fire_penalty * fault_penalty
            if cap >= 8.0 and st.health > 20.0:
                effective_capacity[(st.x, st.y)] = cap
                active_stations.append(st)
                st.powered = True
            else:
                effective_capacity[(st.x, st.y)] = 0.0
                st.powered = False

        # Build local transmission graph (each consumer connects to nearest power station within radius or relay)
        adj: dict[Coord, list[Coord]] = {c: [] for c in tile_map}
        links: list[PowerLink] = []

        # Connect stations to nearby substations/buildings within transmission span
        station_coords = [(s.x, s.y) for s in active_stations]
        total_supply = sum(effective_capacity.values())

        # Determine priority order when load shedding is active
        def consumer_priority(t: TileState) -> int:
            if t.tile_type in (TileType.HOSPITAL, TileType.SHELTER):
                return 0
            if t.tile_type in (TileType.ROAD, TileType.SCHOOL):
                return 1
            if t.tile_type == TileType.RESIDENTIAL:
                return 2
            return 3  # Industry shed first during load shedding

        sorted_consumers = sorted(consumers, key=consumer_priority)

        # Assign each consumer to nearest active station via Manhattan distance
        assigned_load: dict[Coord, float] = {sc: 0.0 for sc in station_coords}
        station_assignments: dict[Coord, list[TileState]] = {sc: [] for sc in station_coords}

        for consumer in sorted_consumers:
            if not station_coords:
                continue
            nearest_st = min(
                station_coords,
                key=lambda sc: abs(sc[0] - consumer.x) + abs(sc[1] - consumer.y),
            )
            dist = abs(nearest_st[0] - consumer.x) + abs(nearest_st[1] - consumer.y)
            # Power lines can reach up to 18 grid units (city-wide distribution), reduced if severe damage
            if dist <= 22:
                station_assignments[nearest_st].append(consumer)
                assigned_load[nearest_st] += consumer.power_load_mw

        # Check station overloads & cascading failures
        overloaded_count = 0
        for sc in list(station_coords):
            cap = effective_capacity[sc]
            load = assigned_load[sc]
            if load > cap * 1.15:
                overloaded_count += 1
                if not load_shedding_active:
                    # Station suffers thermal overload damage -> risk of cascading trip!
                    st_tile = tile_map[sc]
                    st_tile.health = max(0.0, st_tile.health - 4.5)
                    if load > cap * 1.45:
                        effective_capacity[sc] *= 0.45
                        events.append(
                            f"Power cascade: Station ({sc[0]},{sc[1]}) overloaded ({load:.1f}/{cap:.1f} MW) and brownout-tripped."
                        )

        self.overloaded_stations = overloaded_count

        # Allocate power along edges & construct adjacency for BFS/DFS verification
        powered_consumers = 0
        for sc, assigned in station_assignments.items():
            remaining_mw = effective_capacity.get(sc, 0.0)
            load_ratio = min(1.8, assigned_load[sc] / max(1.0, effective_capacity.get(sc, 1.0)))
            for consumer in assigned:
                # If load shedding is enabled, non-critical industry is intentionally shed when grid strained
                if load_shedding_active and consumer.tile_type == TileType.INDUSTRY and load_ratio > 0.85:
                    links.append(
                        PowerLink(
                            source=sc,
                            target=(consumer.x, consumer.y),
                            powered=False,
                            load_ratio=round(load_ratio, 2),
                        )
                    )
                    continue

                if remaining_mw >= consumer.power_load_mw * 0.5 and consumer.fire_intensity < 0.7:
                    remaining_mw -= consumer.power_load_mw
                    consumer.powered = True
                    powered_consumers += 1
                    c_coord = (consumer.x, consumer.y)
                    adj[sc].append(c_coord)
                    adj[c_coord].append(sc)
                    if consumer.tile_type in (TileType.HOSPITAL, TileType.SHELTER, TileType.INDUSTRY, TileType.SCHOOL):
                        links.append(
                            PowerLink(
                                source=sc,
                                target=c_coord,
                                powered=True,
                                load_ratio=round(load_ratio, 2),
                            )
                        )
                else:
                    if consumer.tile_type in (TileType.HOSPITAL, TileType.SHELTER):
                        links.append(
                            PowerLink(
                                source=sc,
                                target=(consumer.x, consumer.y),
                                powered=False,
                                load_ratio=round(load_ratio, 2),
                            )
                        )

        # Explicit BFS to count energized power components
        visited_bfs: set[Coord] = set()
        components = 0
        for sc in station_coords:
            if effective_capacity.get(sc, 0.0) <= 0.0 or sc in visited_bfs:
                continue
            components += 1
            q: deque[Coord] = deque([sc])
            visited_bfs.add(sc)
            while q:
                curr = q.popleft()
                for nb in adj.get(curr, []):
                    if nb not in visited_bfs:
                        visited_bfs.add(nb)
                        q.append(nb)

        # Explicit DFS to count critical facilities (hospitals & shelters) reachable from live stations
        visited_dfs: set[Coord] = set()
        critical_reachable = 0
        for sc in station_coords:
            if effective_capacity.get(sc, 0.0) <= 0.0:
                continue
            stack: list[Coord] = [sc]
            while stack:
                node = stack.pop()
                if node in visited_dfs:
                    continue
                visited_dfs.add(node)
                t = tile_map.get(node)
                if t and t.tile_type in CRITICAL_TYPES and t.powered:
                    critical_reachable += 1
                for nb in adj.get(node, []):
                    if nb not in visited_dfs:
                        stack.append(nb)

        self.bfs_components = components
        self.dfs_critical_reachable = critical_reachable

        total_consumers = max(1, len(consumers))
        coverage = round((powered_consumers / total_consumers) * 100.0, 1)
        if total_supply <= 0.0:
            coverage = 0.0
        return coverage, links, events
