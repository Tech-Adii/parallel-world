"""Curated city presets and tile configuration metadata."""

from __future__ import annotations

from app.models.city import TileState, TileType


TILE_SPECS: dict[TileType, dict[str, float | int]] = {
    TileType.EMPTY: {"population": 0, "capacity": 0, "power_load_mw": 0.0, "power_supply_mw": 0.0},
    TileType.WATER: {"population": 0, "capacity": 0, "power_load_mw": 0.0, "power_supply_mw": 0.0},
    TileType.ROAD: {"population": 0, "capacity": 0, "power_load_mw": 0.4, "power_supply_mw": 0.0},
    TileType.RESIDENTIAL: {"population": 420, "capacity": 0, "power_load_mw": 3.5, "power_supply_mw": 0.0},
    TileType.HOSPITAL: {"population": 140, "capacity": 450, "power_load_mw": 8.0, "power_supply_mw": 0.0},
    TileType.SCHOOL: {"population": 360, "capacity": 0, "power_load_mw": 4.5, "power_supply_mw": 0.0},
    TileType.INDUSTRY: {"population": 190, "capacity": 0, "power_load_mw": 10.5, "power_supply_mw": 0.0},
    TileType.POWER_STATION: {"population": 40, "capacity": 0, "power_load_mw": 0.0, "power_supply_mw": 230.0},
    TileType.SHELTER: {"population": 30, "capacity": 1400, "power_load_mw": 4.0, "power_supply_mw": 0.0},
    TileType.PARK: {"population": 25, "capacity": 0, "power_load_mw": 0.3, "power_supply_mw": 0.0},
}


def make_tile(x: int, y: int, tile_type: TileType, elevation: float = 1.5) -> TileState:
    """Create a TileState with canonical population, capacity, and power attributes."""
    spec = TILE_SPECS[tile_type]
    if tile_type == TileType.WATER:
        elevation = 0.0
    return TileState(
        x=x,
        y=y,
        tile_type=tile_type,
        elevation=round(elevation, 2),
        population=int(spec["population"]),
        capacity=int(spec["capacity"]),
        power_load_mw=float(spec["power_load_mw"]),
        power_supply_mw=float(spec["power_supply_mw"]),
        signal_phase="NS" if (x + y) % 2 == 0 else "EW",
    )


def _grid_from_ascii(
    rows: list[str],
    elevation_fn,
) -> tuple[int, int, list[TileState]]:
    legend: dict[str, TileType] = {
        ".": TileType.EMPTY,
        "~": TileType.WATER,
        "#": TileType.ROAD,
        "R": TileType.RESIDENTIAL,
        "H": TileType.HOSPITAL,
        "S": TileType.SCHOOL,
        "I": TileType.INDUSTRY,
        "P": TileType.POWER_STATION,
        "E": TileType.SHELTER,
        "G": TileType.PARK,
    }
    height = len(rows)
    width = len(rows[0])
    tiles: list[TileState] = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            tt = legend.get(ch, TileType.EMPTY)
            elev = elevation_fn(x, y, tt)
            tiles.append(make_tile(x, y, tt, elev))
    return width, height, tiles


def build_metro_harbor() -> dict:
    """Default 20x14 urban twin: river harbor, bridges, downtown core, suburbs, and highland shelters."""
    ascii_map = [
        "G..E....#....E....GG",
        ".RR#RRRR#RRRR#RRR.E.",
        ".RS#RHH.#.SSR#RIR...",
        "####.####.####.#####",
        ".RR#RII.#.RRP#RII...",
        ".GR#R...#.RRR#RIR...",
        "####.####.####.#####",
        ".RR#RRRR#RRRR#RRR...",
        ".PR#RSH.#.RRR#IIR...",
        "####.####.####.#####",
        ".RR#..G.#..G.#.II...",
        "~~~#~~~~#~~~~#~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~",
    ]
    # Note: let's add two clean N-S avenue corridors & E-W boulevards so every block is road-accessible
    ascii_map = [
        "G.E#RRRR#RRRR#E..GGG",
        ".RR#RRRR#RRRR#RRR.E.",
        ".RS#RHH.#.SSR#RIR...",
        "####################",
        ".RR#RII.#.RRP#RII...",
        ".GR#R...#.RRR#RIR...",
        "####################",
        ".RR#RRRR#RRRR#RRR...",
        ".PR#RSH.#.RRR#IIR...",
        "####################",
        ".RR#..G.#..G.#.II...",
        "~~~#~~~~#~~~~#~~~~~~",
        "~~~###########~~~~~~",
        "~~~~~~~~~~~~~~~~~~~~",
    ]

    def elev(x: int, y: int, tt: TileType) -> float:
        if tt == TileType.WATER:
            return 0.0
        base = 0.6 + (13 - y) * 0.24
        if tt == TileType.SHELTER:
            base += 0.9
        if y == 12 and tt == TileType.ROAD:
            base = 0.75
        return min(4.8, base)

    w, h, tiles = _grid_from_ascii(ascii_map, elev)
    return {
        "id": "metro_harbor",
        "name": "Metro Harbor District",
        "description": "Coastal riverfront metropolis with dual bridges, downtown hospitals, industrial docklands, and highland shelters.",
        "width": w,
        "height": h,
        "tiles": tiles,
    }


def build_silicon_grid() -> dict:
    """20x14 high-density tech corridor with arterial loop and central canal."""
    ascii_map = [
        "E..#....#....#....E.",
        ".RR#RRRR#RRRR#RRR...",
        ".RS#IHH.#.SSI#RRR...",
        "####################",
        ".II#R..P#P..R#III...",
        ".II#R.GG~GG.R#III...",
        "###~####~####~######",
        ".RR#R.GG~GG.R#RRR...",
        ".RR#RRRR#RRRR#RHR...",
        "####################",
        ".SR#RII.#.RRP#RRE...",
        ".RR#RRRR#RRRR#RRR...",
        "####################",
        "G..#..E.#....#....GG",
    ]

    def elev(x: int, y: int, tt: TileType) -> float:
        if tt == TileType.WATER:
            return 0.0
        dist_center = abs(x - 9.5) + abs(y - 6.0)
        base = 0.9 + dist_center * 0.16
        if tt == TileType.SHELTER:
            base += 0.8
        return min(4.5, base)

    w, h, tiles = _grid_from_ascii(ascii_map, elev)
    return {
        "id": "silicon_grid",
        "name": "Silicon Canal Grid",
        "description": "Planned tech metropolis bisected by a central canal with three power plants and dense transit loops.",
        "width": w,
        "height": h,
        "tiles": tiles,
    }


def build_blank_canvas() -> dict:
    """20x14 starter blueprint for custom city creation."""
    rows = ["." * 20 for _ in range(14)]
    rows[6] = "#" * 20
    rows[12] = "~" * 20
    rows[13] = "~" * 20
    for y in range(14):
        row_list = list(rows[y])
        if y < 12:
            row_list[9] = "#"
        rows[y] = "".join(row_list)
    # Place 1 starter power station, 1 hospital, 1 residential, 1 shelter
    def put(x: int, y: int, ch: str) -> None:
        r = list(rows[y])
        r[x] = ch
        rows[y] = "".join(r)

    put(8, 5, "P")
    put(10, 5, "H")
    put(8, 7, "R")
    put(10, 4, "E")

    def elev(x: int, y: int, tt: TileType) -> float:
        if tt == TileType.WATER:
            return 0.0
        return 1.2 + (13 - y) * 0.2

    w, h, tiles = _grid_from_ascii(rows, elev)
    return {
        "id": "blank_canvas",
        "name": "Frontier Sandbox",
        "description": "Minimal starter grid with arterial crossroads and riverfront — build your own city layout.",
        "width": w,
        "height": h,
        "tiles": tiles,
    }


CITY_PRESETS: dict[str, dict] = {
    "metro_harbor": build_metro_harbor(),
    "silicon_grid": build_silicon_grid(),
    "blank_canvas": build_blank_canvas(),
}


def get_preset_blueprint(preset_id: str) -> dict:
    builder_map = {
        "metro_harbor": build_metro_harbor,
        "silicon_grid": build_silicon_grid,
        "blank_canvas": build_blank_canvas,
    }
    fn = builder_map.get(preset_id, build_metro_harbor)
    return fn()
