"""Time Machine: LIFO Stack-based undo, rewind, timeline replay, and alternate-future branching."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from app.models.city import DisasterConfig, InterventionState, TileState, VehicleAgent


@dataclass
class SimulationFrame:
    tick: int
    sim_time_minutes: float
    tiles: list[TileState]
    vehicles: list[VehicleAgent]
    disasters: DisasterConfig
    interventions: InterventionState
    evacuated_citizens: int
    history_curve: list[dict[str, float | int]]
    event_log: list[str]


class TimeMachineStack:
    """Explicit stack data structure enabling O(1) snapshot push and O(k) rewind/undo operations."""

    def __init__(self, max_frames: int = 240) -> None:
        self.max_frames = max_frames
        self._stack: list[SimulationFrame] = []

    def push(self, frame: SimulationFrame) -> None:
        if len(self._stack) >= self.max_frames:
            self._stack.pop(0)
        self._stack.append(copy.deepcopy(frame))

    def pop_steps(self, steps: int = 1) -> SimulationFrame | None:
        """Pop `steps` frames off the stack to rewind to an earlier state."""
        if len(self._stack) <= 1:
            return None
        popped: SimulationFrame | None = None
        actual_steps = min(max(1, steps), len(self._stack) - 1)
        for _ in range(actual_steps):
            self._stack.pop()
        if self._stack:
            popped = copy.deepcopy(self._stack[-1])
        return popped

    def rewind_to_tick(self, target_tick: int) -> SimulationFrame | None:
        """Pop stack frames until reaching target_tick (allowing an alternate timeline branch)."""
        if not self._stack:
            return None
        while len(self._stack) > 1 and self._stack[-1].tick > target_tick:
            self._stack.pop()
        return copy.deepcopy(self._stack[-1])

    def available_ticks(self) -> list[int]:
        return [frame.tick for frame in self._stack]

    def depth(self) -> int:
        return len(self._stack)

    def clear(self) -> None:
        self._stack.clear()
