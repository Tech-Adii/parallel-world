"""FastAPI + WebSocket server for Parallel World: Intelligent City Simulator."""

from __future__ import annotations

import asyncio
import contextlib
import re
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.engine.ai_advisor import AICityAdministrator
from app.engine.presets import CITY_PRESETS
from app.engine.simulation import ParallelWorldManager
from app.models.city import (
    AIAdviceRequest,
    AIAdviceResponse,
    CityPresetInfo,
    DisasterUpdateRequest,
    InterventionRequest,
    RewindRequest,
    SaveCityRequest,
    TileEditRequest,
    TimelineSummary,
)


class SpeedRequest(BaseModel):
    speed: float = 1.0


class ScopeRequest(BaseModel):
    scope: Literal["all", "primary", "parallel"] = "all"


manager = ParallelWorldManager()
advisor = AICityAdministrator()
sim_speed: float = 1.0
ws_clients: set[WebSocket] = set()
state_lock = asyncio.Lock()


async def broadcast_state() -> None:
    if not ws_clients:
        return
    payload = {
        "type": "state_update",
        "speed": sim_speed,
        "primary": manager.primary.snapshot().model_dump(),
        "parallel": manager.parallel_comparison().model_dump(),
    }
    stale: list[WebSocket] = []
    for ws in list(ws_clients):
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        ws_clients.discard(ws)


async def simulation_loop() -> None:
    while True:
        delay = max(0.28, 1.05 / max(0.25, sim_speed))
        await asyncio.sleep(delay)
        async with state_lock:
            if manager.primary.running or (manager.universe_a.running and manager.universe_b.running):
                manager.step_all()
        await broadcast_state()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(simulation_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Parallel World: Intelligent Urban Digital Twin API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _list_all_cities() -> list[CityPresetInfo]:
    builtins = [
        CityPresetInfo(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            width=p["width"],
            height=p["height"],
            population=sum(t.population for t in p["tiles"]),
            is_custom=False,
        )
        for p in CITY_PRESETS.values()
    ]
    custom = manager.db.list_custom_cities()
    return builtins + custom


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "parallel-world-backend",
        "tick": manager.primary.tick,
        "sqlite_snapshots": manager.db.snapshot_count(),
    }


@app.get("/api/state")
async def get_full_state() -> dict:
    async with state_lock:
        return {
            "speed": sim_speed,
            "primary": manager.primary.snapshot().model_dump(),
            "parallel": manager.parallel_comparison().model_dump(),
            "cities": [c.model_dump() for c in _list_all_cities()],
        }


@app.post("/api/simulation/play")
async def play_simulation(req: ScopeRequest | None = None) -> dict:
    scope = req.scope if req else "all"
    async with state_lock:
        manager.set_running(True, scope=scope)
    await broadcast_state()
    return {"running": True, "scope": scope}


@app.post("/api/simulation/pause")
async def pause_simulation(req: ScopeRequest | None = None) -> dict:
    scope = req.scope if req else "all"
    async with state_lock:
        manager.set_running(False, scope=scope)
    await broadcast_state()
    return {"running": False, "scope": scope}


@app.post("/api/simulation/step")
async def step_simulation(universe_id: str = "all") -> dict:
    async with state_lock:
        if universe_id == "all":
            manager.primary.step()
            manager.universe_a.step()
            manager.universe_b.step()
        elif universe_id == "parallel":
            manager.universe_a.step()
            manager.universe_b.step()
        else:
            manager.get_universe(universe_id).step()
        primary = manager.primary.snapshot().model_dump()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"primary": primary, "parallel": parallel}


@app.post("/api/simulation/speed")
async def set_speed(req: SpeedRequest) -> dict:
    global sim_speed
    sim_speed = max(0.25, min(4.0, req.speed))
    await broadcast_state()
    return {"speed": sim_speed}


@app.post("/api/simulation/disasters")
async def update_disasters(req: DisasterUpdateRequest, universe_id: str = "primary") -> dict:
    async with state_lock:
        if universe_id == "parallel":
            manager.update_parallel_disasters(req)
        elif universe_id == "all":
            manager.primary.update_disasters(req)
            manager.update_parallel_disasters(req)
        else:
            manager.get_universe(universe_id).update_disasters(req)
        primary = manager.primary.snapshot().model_dump()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"primary": primary, "parallel": parallel}


@app.post("/api/simulation/intervention")
async def apply_intervention(req: InterventionRequest) -> dict:
    async with state_lock:
        sim = manager.get_universe(req.universe_id)
        sim.apply_action(req.action)
        primary = manager.primary.snapshot().model_dump()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"primary": primary, "parallel": parallel}


@app.post("/api/simulation/tile")
async def edit_tile(req: TileEditRequest, universe_id: str = "primary") -> dict:
    async with state_lock:
        sim = manager.get_universe(universe_id)
        ok = sim.edit_tile(req)
        if not ok:
            raise HTTPException(status_code=400, detail="Tile coordinates out of bounds")
        primary = manager.primary.snapshot().model_dump()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"primary": primary, "parallel": parallel}


@app.post("/api/parallel/sync")
async def sync_parallel_universes() -> dict:
    async with state_lock:
        manager.sync_parallel_from_primary()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"parallel": parallel}


@app.post("/api/parallel/reset")
async def reset_parallel_universes() -> dict:
    async with state_lock:
        manager.reset_parallel()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"parallel": parallel}


@app.get("/api/timemachine/{universe_id}", response_model=TimelineSummary)
async def get_timeline(universe_id: str) -> TimelineSummary:
    async with state_lock:
        sim = manager.get_universe(universe_id)
        ticks = sim.time_machine.available_ticks()
        return TimelineSummary(
            universe_id=sim.universe_id,
            current_tick=sim.tick,
            stack_depth=sim.time_machine.depth(),
            available_ticks=ticks,
            can_undo=len(ticks) > 1,
            latest_events=sim.event_log[-6:],
        )


@app.post("/api/timemachine/rewind")
async def rewind_timeline(req: RewindRequest) -> dict:
    async with state_lock:
        sim = manager.get_universe(req.universe_id)
        ok = sim.rewind(target_tick=req.target_tick, steps=req.steps)
        if not ok:
            raise HTTPException(status_code=400, detail="Cannot rewind further back on Time Machine stack")
        primary = manager.primary.snapshot().model_dump()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"rewound_to_tick": sim.tick, "primary": primary, "parallel": parallel}


@app.post("/api/ai/advice", response_model=AIAdviceResponse)
async def get_ai_advice(req: AIAdviceRequest) -> AIAdviceResponse:
    async with state_lock:
        snapshot = manager.get_universe(req.universe_id).snapshot()
    return advisor.analyze(snapshot, question=req.question)


@app.get("/api/cities", response_model=list[CityPresetInfo])
async def list_cities() -> list[CityPresetInfo]:
    return _list_all_cities()


@app.post("/api/cities/load/{city_id}")
async def load_city(city_id: str) -> dict:
    async with state_lock:
        manager.load_city_blueprint(city_id)
        primary = manager.primary.snapshot().model_dump()
        parallel = manager.parallel_comparison().model_dump()
    await broadcast_state()
    return {"primary": primary, "parallel": parallel}


@app.post("/api/cities/save", response_model=CityPresetInfo)
async def save_city(req: SaveCityRequest) -> CityPresetInfo:
    slug = re.sub(r"[^a-z0-9]+", "_", req.name.lower()).strip("_") or "custom_city"
    blueprint_id = f"custom_{slug}"
    async with state_lock:
        sim = manager.get_universe(req.universe_id)
        saved = manager.db.save_city_blueprint(
            blueprint_id=blueprint_id,
            name=req.name,
            description=req.description,
            width=sim.width,
            height=sim.height,
            tiles=list(sim.tile_map.values()),
        )
    return saved


@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket) -> None:
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        async with state_lock:
            await websocket.send_json(
                {
                    "type": "state_update",
                    "speed": sim_speed,
                    "primary": manager.primary.snapshot().model_dump(),
                    "parallel": manager.parallel_comparison().model_dump(),
                }
            )
        while True:
            # Keep connection alive and allow ping/keepalive messages
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_clients.discard(websocket)
    except Exception:
        ws_clients.discard(websocket)
