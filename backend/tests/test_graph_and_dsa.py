"""Unit tests for road network graph, A* pathfinding, Dijkstra evacuation, and FIFO traffic queues."""

from app.engine.graph_router import RoadNetworkRouter
from app.engine.presets import make_tile
from app.models.city import TileType


def _build_mini_grid():
    tiles = {}
    for y in range(5):
        for x in range(5):
            tiles[(x, y)] = make_tile(x, y, TileType.EMPTY, 2.0)
    # Two horizontal corridors at y=1 and y=3, connected at x=0 and x=4
    for x in range(5):
        tiles[(x, 1)] = make_tile(x, 1, TileType.ROAD, 2.0)
        tiles[(x, 3)] = make_tile(x, 3, TileType.ROAD, 2.0)
    for y in (2,):
        tiles[(0, y)] = make_tile(0, y, TileType.ROAD, 2.0)
        tiles[(4, y)] = make_tile(4, y, TileType.ROAD, 2.0)
    tiles[(0, 0)] = make_tile(0, 0, TileType.RESIDENTIAL, 2.0)
    tiles[(4, 4)] = make_tile(4, 4, TileType.SHELTER, 3.0)
    return tiles


def test_astar_reroutes_around_blocked_road():
    tiles = _build_mini_grid()
    router = RoadNetworkRouter(5, 5)
    router.rebuild_graph(tiles, alternative_routes=True)

    direct = router.astar_path((0, 1), (4, 1))
    assert direct == [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]

    # Block middle of top corridor -> A* must detour via lower corridor y=3
    tiles[(2, 1)].road_blocked = True
    router.rebuild_graph(tiles, alternative_routes=True)
    detour = router.astar_path((0, 1), (4, 1))
    assert detour
    assert (2, 1) not in detour
    assert (2, 3) in detour


def test_dijkstra_evacuation_and_traffic_queues():
    tiles = _build_mini_grid()
    router = RoadNetworkRouter(5, 5)
    router.rebuild_graph(tiles, alternative_routes=True)

    routes = router.dijkstra_evacuation_routes(
        tile_map=tiles,
        affected_origins=[((0, 0), 200)],
        shelters=[tiles[(4, 4)]],
    )
    assert len(routes) == 1
    assert routes[0].shelter == (4, 4)
    assert routes[0].path[0] == (0, 1)
    assert routes[0].path[-1] == (4, 3)

    # Queue operations drain cleanly
    router.intersection_queues[(1, 1)].extend(["V1", "V2", "V3", "V4"])
    remaining = router.update_traffic_queues(tiles, tick=2, alternative_routes=True, power_coverage=100.0)
    assert remaining == 1
    assert tiles[(1, 1)].queue_length == 1
