"""Emergency Evacuation System: Priority Queue (heapq) dispatch, shelter allocation, and rescue routing."""

from __future__ import annotations

import heapq

from app.engine.graph_router import Coord, RoadNetworkRouter
from app.models.city import EmergencyIncident, EvacuationRoute, TileState, TileType


class EvacuationDispatchEngine:
    """Prioritizes disaster incidents via min-heap priority queue and allocates safe shelter routes."""

    def __init__(self) -> None:
        self.priority_queue_size: int = 0
        self.top_priority_incident: str = "None"

    def evaluate_and_dispatch(
        self,
        tile_map: dict[Coord, TileState],
        router: RoadNetworkRouter,
        emergency_response_active: bool,
        tick: int,
    ) -> tuple[list[EmergencyIncident], list[EvacuationRoute], int, list[str]]:
        """Scan affected buildings, rank them in a heapq priority queue, and compute Dijkstra shelter routes."""
        events: list[str] = []
        heap: list[tuple[float, int, EmergencyIncident]] = []
        seq = 0

        # Priority weights by building vulnerability (hospitals and schools prioritized highest)
        type_urgency = {
            TileType.HOSPITAL: 1.55,
            TileType.SCHOOL: 1.4,
            TileType.RESIDENTIAL: 1.15,
            TileType.POWER_STATION: 1.25,
            TileType.INDUSTRY: 0.95,
        }

        affected_origins: list[tuple[Coord, int]] = []

        for tile in tile_map.values():
            if tile.tile_type not in type_urgency:
                continue

            hazard = tile.flood_depth * 0.95 + tile.fire_intensity * 1.2 + (0.45 if not tile.powered else 0.0)
            structural_loss = max(0.0, (100.0 - tile.health) / 100.0)
            total_risk = hazard + structural_loss * 0.8

            if total_risk < 0.28:
                continue

            citizens_at_risk = int(tile.population * min(1.0, total_risk * 0.68))
            if citizens_at_risk <= 0 and tile.tile_type != TileType.POWER_STATION:
                continue

            severity = round((total_risk * 55.0 + citizens_at_risk * 0.08) * type_urgency[tile.tile_type], 2)
            kind_label = (
                "Fire Emergency"
                if tile.fire_intensity > 0.25
                else "Flood Isolation"
                if tile.flood_depth > 0.25
                else "Grid Outage / Damage"
            )
            incident = EmergencyIncident(
                id=f"INC-{tile.x}-{tile.y}",
                x=tile.x,
                y=tile.y,
                kind=f"{tile.tile_type.value.replace('_', ' ').title()}: {kind_label}",
                severity=severity,
                citizens_at_risk=citizens_at_risk,
            )
            # Negative severity for max-priority pop from Python heapq min-heap
            heapq.heappush(heap, (-severity, seq, incident))
            seq += 1

            if tile.tile_type in (TileType.RESIDENTIAL, TileType.SCHOOL, TileType.HOSPITAL):
                affected_origins.append(((tile.x, tile.y), max(20, citizens_at_risk)))

        self.priority_queue_size = len(heap)
        ranked_incidents: list[EmergencyIncident] = []
        rank = 1
        while heap:
            _, _, inc = heapq.heappop(heap)
            inc.priority_rank = rank
            if emergency_response_active and rank <= 6:
                inc.assigned_unit = f"UNIT-{rank}"
            ranked_incidents.append(inc)
            rank += 1

        self.top_priority_incident = (
            f"{ranked_incidents[0].kind} @({ranked_incidents[0].x},{ranked_incidents[0].y})"
            if ranked_incidents
            else "None"
        )

        # Compute Dijkstra evacuation routes to shelters
        shelters = [t for t in tile_map.values() if t.tile_type == TileType.SHELTER]
        evac_routes = router.dijkstra_evacuation_routes(
            tile_map=tile_map,
            affected_origins=affected_origins[:12],
            shelters=shelters,
        )

        newly_evacuated = 0
        if emergency_response_active and evac_routes:
            # Actively transfer citizens along valid Dijkstra evacuation corridors into shelters
            shelter_lookup = {(s.x, s.y): s for s in shelters}
            for route in evac_routes[:6]:
                shelter = shelter_lookup.get(route.shelter)
                origin_tile = tile_map.get(route.origin)
                if not shelter or not origin_tile:
                    continue
                available_cap = max(0, shelter.capacity - shelter.occupied)
                batch = min(available_cap, max(10, int(route.citizens * 0.14)), origin_tile.population)
                if batch > 0:
                    shelter.occupied += batch
                    origin_tile.population = max(0, origin_tile.population - batch)
                    newly_evacuated += batch

            if newly_evacuated > 0 and tick % 3 == 0:
                events.append(
                    f"Evacuation dispatch moved {newly_evacuated} citizens via Dijkstra corridors to shelters."
                )

        return ranked_incidents[:12], evac_routes, newly_evacuated, events
