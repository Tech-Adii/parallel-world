import { useEffect, useState } from "react";
import { History, Rewind, Undo2 } from "lucide-react";
import { api } from "../api/client";
import type { TimelineSummary, UniverseSnapshot } from "../types/simulation";

interface TimeMachineBarProps {
  snapshot: UniverseSnapshot;
  onRewind: (opts: { target_tick?: number; steps?: number }) => void;
}

export function TimeMachineBar({ snapshot, onRewind }: TimeMachineBarProps) {
  const [timeline, setTimeline] = useState<TimelineSummary | null>(null);
  const [selectedTick, setSelectedTick] = useState<number>(snapshot.tick);

  useEffect(() => {
    let active = true;
    api
      .getTimeline(snapshot.universe_id)
      .then((res) => {
        if (active) {
          setTimeline(res);
          setSelectedTick(res.current_tick);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [snapshot.tick, snapshot.universe_id]);

  const ticks = timeline?.available_ticks ?? [0];
  const minTick = ticks[0] ?? 0;
  const maxTick = ticks[ticks.length - 1] ?? snapshot.tick;

  return (
    <div className="timeline-bar">
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <History size={16} color="#a78bfa" />
        <strong style={{ fontSize: 12.5, letterSpacing: "0.04em" }}>TIME MACHINE</strong>
        <span className="mono" style={{ fontSize: 11, color: "#94a3b8" }}>
          Stack: {snapshot.cs_metrics.undo_stack_depth} frames
        </span>
      </div>

      <button
        type="button"
        className="btn"
        disabled={!timeline?.can_undo}
        onClick={() => onRewind({ steps: 1 })}
        title="Pop 1 snapshot frame from Undo Stack"
      >
        <Undo2 size={13} />
        <span>Undo 1 Tick</span>
      </button>

      <button
        type="button"
        className="btn"
        disabled={snapshot.tick < 5}
        onClick={() => onRewind({ steps: 5 })}
      >
        <Rewind size={13} />
        <span>-5 Ticks</span>
      </button>

      <div style={{ flex: 1, minWidth: 180, display: "flex", alignItems: "center", gap: 10 }}>
        <span className="mono" style={{ fontSize: 11, color: "#64748b" }}>
          T+{minTick}
        </span>
        <input
          type="range"
          min={minTick}
          max={Math.max(minTick, maxTick)}
          value={Math.min(maxTick, Math.max(minTick, selectedTick))}
          onChange={(e) => setSelectedTick(Number(e.target.value))}
          style={{ flex: 1, accentColor: "#a78bfa" }}
        />
        <span className="mono" style={{ fontSize: 11, color: "#c4b5fd" }}>
          T+{selectedTick}
        </span>
      </div>

      <button
        type="button"
        className="btn btn-primary"
        disabled={selectedTick >= snapshot.tick || ticks.length <= 1}
        onClick={() => onRewind({ target_tick: selectedTick })}
      >
        Branch from T+{selectedTick}
      </button>
    </div>
  );
}
