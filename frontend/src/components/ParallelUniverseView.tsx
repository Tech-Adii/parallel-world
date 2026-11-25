import { GitBranch, Navigation, RefreshCw, ShieldAlert, Zap } from "lucide-react";
import type { MapOverlayMode, ParallelComparison } from "../types/simulation";
import { CityCanvas2D } from "./CityCanvas2D";

interface ParallelUniverseViewProps {
  parallel: ParallelComparison;
  overlayMode: MapOverlayMode;
  onSyncFromPrimary: () => void;
  onResetParallel: () => void;
  onAction: (
    universeId: "universe_a" | "universe_b",
    action: "toggle_emergency_response" | "toggle_alternative_routes" | "toggle_load_shedding"
  ) => void;
}

export function ParallelUniverseView({
  parallel,
  overlayMode,
  onSyncFromPrimary,
  onResetParallel,
  onAction,
}: ParallelUniverseViewProps) {
  const { universe_a: ua, universe_b: ub } = parallel;

  const renderUniverseCard = (
    u: typeof ua,
    variant: "u-a" | "u-b",
    accentColor: string,
    uid: "universe_a" | "universe_b"
  ) => (
    <section className={`universe-card ${variant}`}>
      <div className="panel-header" style={{ marginBottom: 0 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: accentColor }}>{u.label}</h3>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>{u.strategy_description}</div>
        </div>
        <span className="mono" style={{ fontSize: 12, color: "#cbd5e1" }}>
          T+{u.tick}
        </span>
      </div>

      <div className="universe-hero">
        <div>
          <div style={{ fontSize: 11, color: "#94a3b8" }}>City stability</div>
          <div className="hero-percent mono" style={{ color: accentColor }}>
            {u.metrics.city_stability.toFixed(0)}%
          </div>
        </div>
        <div className="stat-row">
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Citizens affected</div>
            <strong className="mono" style={{ fontSize: 15 }}>
              {u.metrics.citizens_affected.toLocaleString()}
            </strong>
          </div>
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Blocked roads</div>
            <strong className="mono" style={{ fontSize: 15 }}>
              {u.metrics.blocked_roads}
            </strong>
          </div>
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Recovery</div>
            <strong className="mono" style={{ fontSize: 15 }}>
              {u.metrics.recovery_hours}h
            </strong>
          </div>
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Services active</div>
            <strong className="mono">{u.metrics.services_active.toFixed(0)}%</strong>
          </div>
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Power coverage</div>
            <strong className="mono">{u.metrics.power_coverage.toFixed(0)}%</strong>
          </div>
          <div>
            <div style={{ color: "#94a3b8", fontSize: 11 }}>Evacuated</div>
            <strong className="mono">{u.metrics.evacuated_citizens.toLocaleString()}</strong>
          </div>
        </div>
      </div>

      <CityCanvas2D snapshot={u} overlayMode={overlayMode} heightPx={320} />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        <button
          type="button"
          className={`btn ${u.interventions.emergency_response_active ? "btn-emerald" : ""}`}
          onClick={() => onAction(uid, "toggle_emergency_response")}
        >
          <ShieldAlert size={13} />
          <span>Emergency: {u.interventions.emergency_response_active ? "ON" : "OFF"}</span>
        </button>
        <button
          type="button"
          className={`btn ${u.interventions.alternative_routes_active ? "btn-active" : ""}`}
          onClick={() => onAction(uid, "toggle_alternative_routes")}
        >
          <Navigation size={13} />
          <span>A* Reroute: {u.interventions.alternative_routes_active ? "ON" : "OFF"}</span>
        </button>
        <button
          type="button"
          className={`btn ${u.interventions.load_shedding_active ? "btn-active" : ""}`}
          onClick={() => onAction(uid, "toggle_load_shedding")}
        >
          <Zap size={13} />
          <span>Load Shedding: {u.interventions.load_shedding_active ? "ON" : "OFF"}</span>
        </button>
      </div>
    </section>
  );

  // Build SVG polyline points for stability comparison
  const pointsA = ua.history_curve;
  const pointsB = ub.history_curve;
  const maxLen = Math.max(2, pointsA.length, pointsB.length);
  const toSvg = (pts: typeof pointsA) =>
    pts
      .map((p, idx) => {
        const x = (idx / Math.max(1, maxLen - 1)) * 560 + 20;
        const y = 110 - (p.stability / 100) * 90;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="panel" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h2 className="panel-title" style={{ marginBottom: 4 }}>
            <GitBranch size={15} color="#38bdf8" />
            Parallel Universes — Simultaneous Counterfactual Simulation
          </h2>
          <div style={{ fontSize: 12.5, color: "#94a3b8" }}>
            Run identical city layouts and disaster seeds side-by-side to quantify emergency policy outcomes without altering your primary world.
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
          <div className="mono" style={{ fontSize: 12.5, padding: "7px 12px", borderRadius: 9, background: "rgba(16, 185, 129, 0.14)", border: "1px solid rgba(16, 185, 129, 0.35)", color: "#6ee7b7" }}>
            Outcome Delta (B vs A):{" "}
            <strong>
              {parallel.delta_stability >= 0 ? "+" : ""}
              {parallel.delta_stability}% stability
            </strong>{" "}
            · <strong>{parallel.delta_citizens_affected.toLocaleString()} fewer affected</strong> ·{" "}
            <strong>{parallel.delta_recovery_hours}h faster recovery</strong>
          </div>

          <button type="button" className="btn btn-primary" onClick={onSyncFromPrimary}>
            <RefreshCw size={13} />
            <span>Clone Primary City & Disasters</span>
          </button>
          <button type="button" className="btn" onClick={onResetParallel}>
            Reset A vs B
          </button>
        </div>
      </div>

      <div className="parallel-grid">
        {renderUniverseCard(ua, "u-a", "#fb7185", "universe_a")}
        {renderUniverseCard(ub, "u-b", "#34d399", "universe_b")}
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Stability Divergence Over Time (Universe A vs Universe B)</h3>
          <div style={{ display: "flex", gap: 14, fontSize: 12 }}>
            <span style={{ color: "#fb7185" }}>● Universe A ({ua.metrics.city_stability.toFixed(0)}%)</span>
            <span style={{ color: "#34d399" }}>● Universe B ({ub.metrics.city_stability.toFixed(0)}%)</span>
          </div>
        </div>
        <svg viewBox="0 0 600 125" style={{ width: "100%", height: 125, display: "block" }}>
          <line x1="20" y1="20" x2="580" y2="20" stroke="rgba(148,163,184,0.15)" strokeDasharray="4" />
          <line x1="20" y1="65" x2="580" y2="65" stroke="rgba(148,163,184,0.15)" strokeDasharray="4" />
          <line x1="20" y1="110" x2="580" y2="110" stroke="rgba(148,163,184,0.22)" />
          <text x="4" y="24" fill="#64748b" fontSize="9">
            100%
          </text>
          <text x="6" y="68" fill="#64748b" fontSize="9">
            50%
          </text>
          <text x="10" y="112" fill="#64748b" fontSize="9">
            0%
          </text>
          {pointsA.length > 1 && (
            <polyline fill="none" stroke="#fb7185" strokeWidth="2.5" points={toSvg(pointsA)} />
          )}
          {pointsB.length > 1 && (
            <polyline fill="none" stroke="#34d399" strokeWidth="2.5" points={toSvg(pointsB)} />
          )}
        </svg>
      </div>
    </div>
  );
}
