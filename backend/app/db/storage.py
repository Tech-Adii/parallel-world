"""SQLite persistence for custom city blueprints, simulation history snapshots, and universe benchmark runs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models.city import CityPresetInfo, TileState


class SimulationDatabase:
    """Thread-safe lightweight SQLite wrapper for storing cities and simulation history."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            data_dir = Path(__file__).resolve().parents[2] / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "parallel_world.db"
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS city_blueprints (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    population INTEGER NOT NULL,
                    tiles_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS simulation_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    universe_id TEXT NOT NULL,
                    city_name TEXT NOT NULL,
                    tick INTEGER NOT NULL,
                    stability REAL NOT NULL,
                    citizens_affected INTEGER NOT NULL,
                    blocked_roads INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def save_city_blueprint(
        self,
        blueprint_id: str,
        name: str,
        description: str,
        width: int,
        height: int,
        tiles: list[TileState],
    ) -> CityPresetInfo:
        pop = sum(t.population for t in tiles)
        tiles_json = json.dumps([t.model_dump() for t in tiles])
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO city_blueprints (id, name, description, width, height, population, tiles_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (blueprint_id, name, description, width, height, pop, tiles_json),
            )
            conn.commit()
        return CityPresetInfo(
            id=blueprint_id,
            name=name,
            description=description,
            width=width,
            height=height,
            population=pop,
            is_custom=True,
        )

    def list_custom_cities(self) -> list[CityPresetInfo]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, description, width, height, population FROM city_blueprints ORDER BY created_at DESC"
            ).fetchall()
        return [
            CityPresetInfo(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                width=row["width"],
                height=row["height"],
                population=row["population"],
                is_custom=True,
            )
            for row in rows
        ]

    def load_custom_city(self, blueprint_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, description, width, height, tiles_json FROM city_blueprints WHERE id = ?",
                (blueprint_id,),
            ).fetchone()
        if not row:
            return None
        tiles = [TileState(**item) for item in json.loads(row["tiles_json"])]
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "width": row["width"],
            "height": row["height"],
            "tiles": tiles,
        }

    def record_snapshot(
        self,
        universe_id: str,
        city_name: str,
        tick: int,
        stability: float,
        citizens_affected: int,
        blocked_roads: int,
        summary_payload: dict,
    ) -> int:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO simulation_snapshots
                (universe_id, city_name, tick, stability, citizens_affected, blocked_roads, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    universe_id,
                    city_name,
                    tick,
                    stability,
                    citizens_affected,
                    blocked_roads,
                    json.dumps(summary_payload),
                ),
            )
            count = conn.execute("SELECT COUNT(*) FROM simulation_snapshots").fetchone()[0]
            conn.commit()
        return int(count)

    def snapshot_count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM simulation_snapshots").fetchone()[0])
