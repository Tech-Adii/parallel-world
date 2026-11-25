"""Unit tests for Flood/Fire Cellular Automata, SimPy discrete events, and Power Grid BFS/DFS cascades."""

from app.engine.disasters import DisasterEngine
from app.engine.power_grid import PowerGridSimulator
from app.engine.presets import get_preset_blueprint
from app.models.city import DisasterConfig, TileType


def test_flood_and_fire_cellular_automata_propagate():
    bp = get_preset_blueprint("metro_harbor")
    tile_map = {(t.x, t.y): t for t in bp["tiles"]}
    engine = DisasterEngine(bp["width"], bp["height"], seed=7)
    disasters = DisasterConfig(flood=True, fire=True, intensity=80)

    flood_cells = 0
    fire_cells = 0
    for tick in range(1, 7):
        flood_cells, fire_cells, _ = engine.step(tile_map, disasters, emergency_response_active=False, tick=tick)

    assert flood_cells > 0
    assert fire_cells > 0
    assert engine.simpy_events_processed >= 6
    assert engine.simpy_env.now == 6.0


def test_power_grid_bfs_dfs_and_load_shedding():
    bp = get_preset_blueprint("metro_harbor")
    tile_map = {(t.x, t.y): t for t in bp["tiles"]}
    grid = PowerGridSimulator()

    cov_normal, links_normal, _ = grid.step(
        tile_map, power_failure_active=False, intensity=0, load_shedding_active=False
    )
    assert cov_normal > 85.0
    assert grid.bfs_components >= 1
    assert grid.dfs_critical_reachable >= 2
    assert len(links_normal) > 0

    # Severe power failure without load shedding drops coverage sharply
    cov_fault, _, _ = grid.step(
        tile_map, power_failure_active=True, intensity=90, load_shedding_active=False
    )
    # With load shedding active, critical hospitals/shelters are prioritized
    cov_shed, links_shed, _ = grid.step(
        tile_map, power_failure_active=True, intensity=90, load_shedding_active=True
    )
    assert cov_fault < cov_normal
    critical_powered = sum(
        1
        for t in tile_map.values()
        if t.tile_type in (TileType.HOSPITAL, TileType.SHELTER) and t.powered
    )
    assert critical_powered >= 1
    assert len(links_shed) > 0
