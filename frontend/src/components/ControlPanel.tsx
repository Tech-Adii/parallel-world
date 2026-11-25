import {
  Activity,
  AlertTriangle,
  Flame,
  Navigation,
  RotateCcw,
  ShieldAlert,
  TrafficCone,
  Waves,
  Zap,
  ZapOff,
} from "lucide-react";
import type { DisasterConfig, UniverseSnapshot } from "../types/simulation";

interface ControlPanelProps {
  snapshot: UniverseSnapshot;
  onToggleDisaster: (key: keyof Omit<DisasterConfig, "intensity">) => void;
  onChangeIntensity: (value: number) => void;
  onAction: (
    action:
      | "deploy_emergency_response"
      | "toggle_emergency_response"
      | "activate_alternative_routes"
      | "toggle_alternative_routes"
      | "toggle_load_shedding"
      | "clear_road_blockages"
      | "reset"
  ) => void;
}

export function ControlPanel({
  snapshot,
  onToggleDisaster,
  onChangeIntensity,
  onAction,
}: ControlPanelProps) {
  const { disasters, interventions, metrics } = snapshot;

  const disasterButtons: {
    key: keyof Omit<DisasterConfig, "intensity">;
    label: string;
    emoji: string;
    icon: JSX.Element;
  }[] = [
    { key: "flood", label: "Flood", emoji: "🌊", icon: <Waves size={14} /> },
    { key: "traffic", label: "Traffic jam", emoji: "🚗", icon: <TrafficCone size={14} /> },
    { key: "power_failure", label: "Power failure", emoji: "⚡", icon: <ZapOff size={14} /> },
    { key: "fire", label: "Urban fire", emoji: "🔥", icon: <Flame size={14} /> },
    { key: "earthquake", label: "Earthquake", emoji: "🌋", icon: <Activity size={14} /> },
    { key: "road_blockage", label: "Road blockage", emoji: "🚧", icon: <AlertTriangle size={14} /> },
  ];

  const stabilityColor =
    metrics.city_stability >= 72
      ? "#10b981"
      : metrics.city_stability >= 45
        ? "#f59e0b"
        : "#f43f5e";

  return (
    <aside className="panel" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="panel-header" style={{ marginBottom: 4 }}>
        <h2 className="panel-title">
          <ShieldAlert size={15} color="#38bdf8" />
          Disaster Control Panel
        </h2>
        <span className="mono" style={{ fontSize: 11, color: "#94a3b8" }}>
          SimPy {metrics.sim_time_minutes}m
        </span>
      </div>

      <div className="disaster-grid">
        {disasterButtons.map((d) => {
          const active = disasters[d.key];
          return (
            <button
              key={d.key}
              type="button"
              className={`disaster-chip ${active ? "on" : ""}`}
              onClick={() => onToggleDisaster(d.key)}
            >
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <span>{d.emoji}</span>
                <span>{d.label}</span>
              </span>
              <span className="mono" style={{ fontSize: 10 }}>
                {active ? "ON" : "OFF"}
              </span>
            </button>
          );
        })}
      </div>

      <div className="slider-row">
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
          <span style={{ color: "#cbd5e1", fontWeight: 600 }}>Disaster intensity</span>
          <span className="mono" style={{ color: "#38bdf8", fontWeight: 700 }}>
            {disasters.intensity}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={disasters.intensity}
          onChange={(e) => onChangeIntensity(Number(e.target.value))}
        />
      </div>

      {/* Hero KPI Cards matching concept design */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">City stability</div>
          <div className="kpi-value mono" style={{ color: stabilityColor }}>
            {metrics.city_stability.toFixed(0)}%
          </div>
          <div className="kpi-sub">Rec: ~{metrics.recovery_hours}h</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Citizens affected</div>
          <div className="kpi-value mono" style={{ color: "#fb7185" }}>
            {metrics.citizens_affected.toLocaleString()}
          </div>
          <div className="kpi-sub">Evac: {metrics.evacuated_citizens.toLocaleString()}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Services active</div>
          <div className="kpi-value mono" style={{ color: "#38bdf8" }}>
            {metrics.services_active.toFixed(0)}%
          </div>
          <div className="kpi-sub">Grid: {metrics.power_coverage.toFixed(0)}%</div>
        </div>
      </div>

      {/* Secondary telemetry row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 6,
          fontSize: 11.5,
          padding: "8px 10px",
          borderRadius: 9,
          background: "rgba(6, 10, 19, 0.6)",
          border: "1px solid rgba(148,163,184,0.12)",
        }}
      >
        <div>
          Blocked roads: <strong className="mono">{metrics.blocked_roads}</strong>
        </div>
        <div>
          Congestion: <strong className="mono">{metrics.avg_congestion}%</strong>
        </div>
        <div>
          Flooded cells: <strong className="mono">{metrics.flooded_tiles}</strong>
        </div>
        <div>
          Active fires: <strong className="mono">{metrics.active_fires}</strong>
        </div>
      </div>

      {/* Primary intervention action buttons */}
      <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 4 }}>
        <button
          type="button"
          className={`btn ${interventions.emergency_response_active ? "btn-emerald" : "btn-primary"}`}
          onClick={() => onAction("toggle_emergency_response")}
        >
          <ShieldAlert size={14} />
          <span>
            {interventions.emergency_response_active
              ? "Emergency response deployed ✓"
              : "Deploy emergency response"}
          </span>
        </button>

        <button
          type="button"
          className={`btn ${interventions.alternative_routes_active ? "btn-active" : ""}`}
          onClick={() => onAction("toggle_alternative_routes")}
        >
          <Navigation size={14} />
          <span>
            {interventions.alternative_routes_active
              ? "Alternative A* routes active ✓"
              : "Activate alternative routes"}
          </span>
        </button>

        <button
          type="button"
          className={`btn ${interventions.load_shedding_active ? "btn-active" : ""}`}
          onClick={() => onAction("toggle_load_shedding")}
        >
          <Zap size={14} />
          <span>
            {interventions.load_shedding_active
              ? "Smart power load shedding ON ✓"
              : "Enable smart load shedding"}
          </span>
        </button>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 }}>
          <button type="button" className="btn" onClick={() => onAction("clear_road_blockages")}>
            Clear roads
          </button>
          <button type="button" className="btn btn-rose" onClick={() => onAction("reset")}>
            <RotateCcw size={13} />
            <span>Reset simulation</span>
          </button>
        </div>
      </div>

      <p style={{ margin: "4px 0 0", fontSize: 11, color: "#64748b", lineHeight: 1.4 }}>
        Interactive urban digital twin combining cellular automata, NetworkX A*/Dijkstra routing,
        BFS/DFS power grid cascades, and SimPy discrete-event simulation.
      </p>
    </aside>
  );
}
