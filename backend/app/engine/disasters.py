"""Disaster Simulation Engine: NumPy Cellular Automata (Flood & Fire), Earthquake, Blockages, and SimPy Discrete-Event Scheduler."""

from __future__ import annotations

import random

import numpy as np
import simpy

from app.models.city import DisasterConfig, TileState, TileType


Coord = tuple[int, int]

FLAMMABLE_TYPES = {
    TileType.RESIDENTIAL,
    TileType.INDUSTRY,
    TileType.SCHOOL,
    TileType.POWER_STATION,
    TileType.HOSPITAL,
}


class DisasterEngine:
    """Runs Cellular Automata spread on NumPy grids and schedules discrete disaster events with SimPy."""

    def __init__(self, width: int, height: int, seed: int = 42) -> None:
        self.width = width
        self.height = height
        self.rng = random.Random(seed)
        self.simpy_env = simpy.Environment()
        self.simpy_events_processed: int = 0
        self._pending_scheduled_events: list[str] = []

    def _schedule_simpy_event(self, delay: float, label: str) -> None:
        def _proc(env: simpy.Environment):
            yield env.timeout(delay)
            self.simpy_events_processed += 1
            self._pending_scheduled_events.append(label)

        self.simpy_env.process(_proc(self.simpy_env))

    def step(
        self,
        tile_map: dict[Coord, TileState],
        disasters: DisasterConfig,
        emergency_response_active: bool,
        tick: int,
    ) -> tuple[int, int, list[str]]:
        """Advance SimPy DES clock by 1.0 minute and run Flood + Fire Cellular Automata."""
        events: list[str] = []
        intensity_factor = disasters.intensity / 100.0

        # Schedule SimPy discrete events for dynamic disaster surges or aftershocks
        if disasters.earthquake and tick % 6 == 1:
            self._schedule_simpy_event(1.0, "Seismic shockwave pulse")
        if disasters.road_blockage and tick % 5 == 1:
            self._schedule_simpy_event(1.0, "Road blockage hazard check")
        if disasters.fire and tick % 4 == 1:
            self._schedule_simpy_event(1.0, "Thermal fire-front expansion")
        if disasters.flood and tick % 3 == 1:
            self._schedule_simpy_event(1.0, "Hydrological flood crest update")

        # Always advance SimPy discrete-event environment by 1 simulation minute
        self._schedule_simpy_event(0.5, "City telemetry heartbeat")
        self.simpy_env.run(until=self.simpy_env.now + 1.0)
        fired_labels = list(self._pending_scheduled_events)
        self._pending_scheduled_events.clear()

        # Build NumPy matrices for Cellular Automata
        flood_grid = np.zeros((self.height, self.width), dtype=np.float32)
        fire_grid = np.zeros((self.height, self.width), dtype=np.float32)
        elev_grid = np.zeros((self.height, self.width), dtype=np.float32)

        for (x, y), tile in tile_map.items():
            flood_grid[y, x] = tile.flood_depth
            fire_grid[y, x] = tile.fire_intensity
            elev_grid[y, x] = tile.elevation

        # 1. FLOOD CELLULAR AUTOMATA
        next_flood = flood_grid.copy()
        if disasters.flood:
            # River / water tiles inject water pressure proportional to disaster intensity
            water_head = min(1.0, 0.25 + intensity_factor * 0.75)
            for (x, y), tile in tile_map.items():
                if tile.tile_type == TileType.WATER:
                    next_flood[y, x] = water_head

            # 4-neighbor CA propagation rule: water flows downhill or spreads laterally when head > elevation threshold
            for y in range(self.height):
                for x in range(self.width):
                    tile = tile_map[(x, y)]
                    if tile.tile_type == TileType.WATER:
                        continue
                    neighbor_max = 0.0
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx_i, ny_i = x + dx, y + dy
                        if 0 <= nx_i < self.width and 0 <= ny_i < self.height:
                            # Effective hydraulic head
                            head = flood_grid[ny_i, nx_i] + elev_grid[ny_i, nx_i] * 0.22
                            if head > neighbor_max:
                                neighbor_max = head

                    terrain_resistance = elev_grid[y, x] * (0.28 if tile.tile_type == TileType.PARK else 0.23)
                    # Emergency sandbagging slows flood advance on higher elevation tiles
                    if emergency_response_active:
                        terrain_resistance += 0.14

                    flood_pressure = (neighbor_max - terrain_resistance) * (0.35 + intensity_factor * 0.55)
                    if flood_pressure > 0.02:
                        target_depth = min(1.0, max(flood_grid[y, x], flood_pressure))
                        next_flood[y, x] = min(1.0, flood_grid[y, x] * 0.65 + target_depth * 0.35)
                    elif emergency_response_active and flood_grid[y, x] > 0.0:
                        next_flood[y, x] = max(0.0, flood_grid[y, x] - 0.06)
        else:
            # Natural drainage when flood disaster is toggled off
            drain_rate = 0.14 if emergency_response_active else 0.07
            next_flood = np.maximum(0.0, flood_grid - drain_rate)

        # 2. URBAN FIRE CELLULAR AUTOMATA
        next_fire = fire_grid.copy()
        if disasters.fire:
            active_fires = int(np.sum(fire_grid > 0.1))
            if active_fires == 0:
                # Seed initial urban fires in industrial / dense residential districts
                candidates = [
                    t
                    for t in tile_map.values()
                    if t.tile_type in (TileType.INDUSTRY, TileType.RESIDENTIAL) and t.flood_depth < 0.2
                ]
                if candidates:
                    seed_count = 2 if intensity_factor >= 0.5 else 1
                    for chosen in self.rng.sample(candidates, min(seed_count, len(candidates))):
                        next_fire[chosen.y, chosen.x] = min(1.0, 0.45 + intensity_factor * 0.4)
                        events.append(f"Urban fire ignited at ({chosen.x},{chosen.y}) [{chosen.tile_type.value}].")

            for y in range(self.height):
                for x in range(self.width):
                    tile = tile_map[(x, y)]
                    if tile.tile_type == TileType.WATER or next_flood[y, x] > 0.35:
                        next_fire[y, x] = 0.0
                        continue
                    curr = fire_grid[y, x]
                    if curr > 0.05:
                        # Fire grows unless suppressed by emergency response
                        if emergency_response_active:
                            next_fire[y, x] = max(0.0, curr - 0.14)
                        else:
                            next_fire[y, x] = min(1.0, curr + 0.08 * (0.4 + intensity_factor))
                    elif tile.tile_type in FLAMMABLE_TYPES:
                        # Check burning neighbors (CA spread rule)
                        burning_neighbors = sum(
                            fire_grid[y + dy, x + dx]
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                            if 0 <= x + dx < self.width and 0 <= y + dy < self.height
                        )
                        if burning_neighbors > 0.35:
                            spread_prob = min(0.75, burning_neighbors * (0.18 + intensity_factor * 0.25))
                            if emergency_response_active:
                                spread_prob *= 0.35
                            if self.rng.random() < spread_prob:
                                next_fire[y, x] = 0.35
                                events.append(f"Fire spread to ({x},{y}) [{tile.tile_type.value}].")
        else:
            suppress = 0.22 if emergency_response_active else 0.08
            next_fire = np.maximum(0.0, fire_grid - suppress)

        # 3. EARTHQUAKE & ROAD BLOCKAGES (driven by SimPy scheduled pulses)
        if "Seismic shockwave pulse" in fired_labels and disasters.earthquake:
            roads = [t for t in tile_map.values() if t.tile_type == TileType.ROAD and not t.road_blocked]
            buildings = [t for t in tile_map.values() if t.tile_type in FLAMMABLE_TYPES]
            rubble_count = max(1, int(len(roads) * 0.06 * max(0.2, intensity_factor)))
            if roads:
                for rt in self.rng.sample(roads, min(rubble_count, len(roads))):
                    if not emergency_response_active or self.rng.random() < 0.4:
                        rt.road_blocked = True
            if buildings:
                for bt in self.rng.sample(buildings, min(4, len(buildings))):
                    bt.health = max(15.0, bt.health - (10.0 + intensity_factor * 18.0))
            events.append(f"Earthquake aftershock damaged {min(4, len(buildings))} structures.")

        if "Road blockage hazard check" in fired_labels and disasters.road_blockage:
            all_roads = [t for t in tile_map.values() if t.tile_type == TileType.ROAD]
            open_roads = [t for t in all_roads if not t.road_blocked]
            blocked_count = len(all_roads) - len(open_roads)
            max_blocked = max(4, int(len(all_roads) * (0.12 if emergency_response_active else 0.30)))
            if open_roads and blocked_count < max_blocked:
                count = max(1, int(2 * intensity_factor))
                if emergency_response_active:
                    count = 1
                chosen = self.rng.sample(open_roads, min(count, len(open_roads), max_blocked - blocked_count))
                for rt in chosen:
                    rt.road_blocked = True
                events.append(f"Traffic incident blocked {len(chosen)} road segment(s).")

        # Emergency crews periodically clear non-flooded road blockages
        cleared_this_tick = 0
        if emergency_response_active and tick % 2 == 0:
            clearable = [
                t
                for t in tile_map.values()
                if t.tile_type == TileType.ROAD and t.road_blocked and t.flood_depth < 0.45
            ]
            if clearable:
                for rt in clearable[:2]:
                    rt.road_blocked = False
                    cleared_this_tick += 1
        if cleared_this_tick > 0:
            events.append(f"Emergency crews cleared {cleared_this_tick} blocked road corridor(s).")

        # Apply updated CA arrays & structural/road impacts back to TileState objects
        ca_flood_cells = 0
        ca_fire_cells = 0
        for (x, y), tile in tile_map.items():
            f_val = round(float(next_flood[y, x]), 3)
            fire_val = round(float(next_fire[y, x]), 3)
            tile.flood_depth = f_val
            tile.fire_intensity = fire_val

            if tile.tile_type != TileType.WATER and f_val > 0.15:
                ca_flood_cells += 1
            if fire_val > 0.08:
                ca_fire_cells += 1

            # Severe flooding blocks roads; fire damages buildings
            if tile.tile_type == TileType.ROAD:
                if f_val >= 0.58:
                    tile.road_blocked = True
                elif not disasters.road_blockage and not disasters.earthquake and f_val < 0.35 and emergency_response_active:
                    # Emergency crews clear roads once flood recedes
                    tile.road_blocked = False
            else:
                damage = f_val * 2.4 + fire_val * 6.5
                if damage > 0.2:
                    tile.health = max(5.0, round(tile.health - damage, 1))
                elif emergency_response_active and tile.health < 100.0 and fire_val < 0.05 and f_val < 0.15:
                    tile.health = min(100.0, round(tile.health + 2.5, 1))

        return ca_flood_cells, ca_fire_cells, events
