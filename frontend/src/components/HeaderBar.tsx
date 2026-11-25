import {
  Activity,
  Cpu,
  GitBranch,
  Hammer,
  Pause,
  Play,
  SkipForward,
  Wifi,
  WifiOff,
} from "lucide-react";
import type { AppViewMode, CityPresetInfo } from "../types/simulation";

interface HeaderBarProps {
  cityName: string;
  tick: number;
  running: boolean;
  speed: number;
  wsConnected: boolean;
  viewMode: AppViewMode;
  cities: CityPresetInfo[];
  onChangeView: (mode: AppViewMode) => void;
  onTogglePlay: () => void;
  onStep: () => void;
  onChangeSpeed: (speed: number) => void;
  onSelectCity: (cityId: string) => void;
}

export function HeaderBar({
  cityName,
  tick,
  running,
  speed,
  wsConnected,
  viewMode,
  cities,
  onChangeView,
  onTogglePlay,
  onStep,
  onChangeSpeed,
  onSelectCity,
}: HeaderBarProps) {
  const tabs: { id: AppViewMode; label: string; icon: JSX.Element }[] = [
    { id: "command", label: "Command Center", icon: <Activity size={14} /> },
    { id: "parallel", label: "Parallel Universes (A vs B)", icon: <GitBranch size={14} /> },
    { id: "builder", label: "City Creation Engine", icon: <Hammer size={14} /> },
    { id: "analytics", label: "CS & DSA Telemetry", icon: <Cpu size={14} /> },
  ];

  return (
    <header className="header-bar">
      <div className="brand-group">
        <div className="brand-logo">PW</div>
        <div>
          <h1 className="brand-title">PARALLEL WORLD</h1>
          <div className="brand-sub">
            Simulate. Decide. Survive. — <span style={{ color: "#38bdf8" }}>{cityName}</span>
          </div>
        </div>

        <div className={`status-pill ${running ? "" : "paused"}`}>
          <span className="pulse-dot" />
          <span>{running ? "Simulation active" : "Simulation paused"}</span>
          <span className="mono" style={{ opacity: 0.85 }}>
            T+{tick}
          </span>
        </div>

        <div
          title={wsConnected ? "Live WebSocket stream connected" : "WebSocket reconnecting..."}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            fontSize: 11,
            color: wsConnected ? "#6ee7b7" : "#fda4af",
          }}
        >
          {wsConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
          <span>{wsConnected ? "WS Live" : "Offline"}</span>
        </div>
      </div>

      <nav className="nav-tabs" aria-label="Workspace modes">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab ${viewMode === tab.id ? "active" : ""}`}
            onClick={() => onChangeView(tab.id)}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      <div className="transport-controls">
        <select
          className="select-dark"
          aria-label="Load city preset"
          onChange={(e) => {
            if (e.target.value) onSelectCity(e.target.value);
          }}
          defaultValue=""
        >
          <option value="" disabled>
            Switch City Blueprint...
          </option>
          {cities.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.population.toLocaleString()} pop){c.is_custom ? " ★" : ""}
            </option>
          ))}
        </select>

        <button
          type="button"
          className={`btn ${running ? "btn-amber" : "btn-emerald"}`}
          onClick={onTogglePlay}
        >
          {running ? <Pause size={14} /> : <Play size={14} />}
          <span>{running ? "Pause" : "Resume"}</span>
        </button>

        <button type="button" className="btn" onClick={onStep} title="Advance 1 tick">
          <SkipForward size={14} />
          <span>Step</span>
        </button>

        <select
          className="select-dark mono"
          aria-label="Simulation speed"
          value={speed}
          onChange={(e) => onChangeSpeed(Number(e.target.value))}
        >
          <option value={0.5}>0.5x</option>
          <option value={1}>1x</option>
          <option value={2}>2x</option>
          <option value={4}>4x</option>
        </select>
      </div>
    </header>
  );
}
