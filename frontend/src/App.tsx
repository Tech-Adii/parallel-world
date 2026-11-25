import { useEffect, useState } from "react";
import { Box, Layers, Terminal } from "lucide-react";
import { api, createSimulationSocket } from "./api/client";
import { AIAdvisorPanel } from "./components/AIAdvisorPanel";
import { CSInspectorPanel } from "./components/CSInspectorPanel";
import { CityBuilderToolbar } from "./components/CityBuilderToolbar";
import { CityCanvas2D } from "./components/CityCanvas2D";
import { CityView3D } from "./components/CityView3D";
import { ControlPanel } from "./components/ControlPanel";
import { HeaderBar } from "./components/HeaderBar";
import { ParallelUniverseView } from "./components/ParallelUniverseView";
import { TimeMachineBar } from "./components/TimeMachineBar";
import type {
  AppViewMode,
  BuilderTool,
  CityPresetInfo,
  DisasterConfig,
  MapOverlayMode,
  ParallelComparison,
  TileState,
  UniverseSnapshot,
} from "./types/simulation";

export default function App() {
  const [primary, setPrimary] = useState<UniverseSnapshot | null>(null);
  const [parallel, setParallel] = useState<ParallelComparison | null>(null);
  const [cities, setCities] = useState<CityPresetInfo[]>([]);
  const [speed, setSpeed] = useState(1);
  const [wsConnected, setWsConnected] = useState(false);
  const [viewMode, setViewMode] = useState<AppViewMode>("command");
  const [overlayMode, setOverlayMode] = useState<MapOverlayMode>("standard");
  const [use3D, setUse3D] = useState(false);
  const [builderTool, setBuilderTool] = useState<BuilderTool>("inspect");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let unmounted = false;

    const loadInitial = async () => {
      try {
        const data = await api.getState();
        if (unmounted) return;
        setPrimary(data.primary);
        setParallel(data.parallel);
        setCities(data.cities);
        setSpeed(data.speed);
        setErrorMsg(null);
      } catch (err) {
        if (!unmounted) {
          setErrorMsg(err instanceof Error ? err.message : "Backend unavailable");
        }
      }
    };

    const connectWs = () => {
      ws = createSimulationSocket(
        (payload) => {
          if (unmounted) return;
          setPrimary(payload.primary);
          setParallel(payload.parallel);
          setSpeed(payload.speed);
          setErrorMsg(null);
        },
        (connected) => {
          if (unmounted) return;
          setWsConnected(connected);
          if (!connected && !reconnectTimer) {
            reconnectTimer = window.setTimeout(() => {
              reconnectTimer = undefined;
              if (!unmounted) connectWs();
            }, 2500);
          }
        }
      );
    };

    loadInitial();
    connectWs();

    return () => {
      unmounted = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  if (!primary || !parallel) {
    return (
      <div className="app-shell" style={{ justifyContent: "center", alignItems: "center" }}>
        <div className="panel" style={{ maxWidth: 460, textAlign: "center" }}>
          <h1 style={{ margin: "0 0 8px", letterSpacing: "0.1em" }}>PARALLEL WORLD</h1>
          <p style={{ color: "#94a3b8", margin: 0 }}>
            {errorMsg
              ? `Connecting to simulation backend... (${errorMsg})`
              : "Bootstrapping Urban Digital Twin & Simulation Engines..."}
          </p>
        </div>
      </div>
    );
  }

  const handleTogglePlay = async () => {
    if (primary.running) {
      await api.pause("all");
    } else {
      await api.play("all");
    }
  };

  const handleStep = async () => {
    const res = await api.step("all");
    setPrimary(res.primary);
    setParallel(res.parallel);
  };

  const handleSpeedChange = async (nextSpeed: number) => {
    setSpeed(nextSpeed);
    await api.setSpeed(nextSpeed);
  };

  const handleSelectCity = async (cityId: string) => {
    const res = await api.loadCity(cityId);
    setPrimary(res.primary);
    setParallel(res.parallel);
  };

  const handleToggleDisaster = async (key: keyof Omit<DisasterConfig, "intensity">) => {
    const nextVal = !primary.disasters[key];
    const res = await api.updateDisasters({ [key]: nextVal }, "primary");
    setPrimary(res.primary);
    setParallel(res.parallel);
  };

  const handleIntensity = async (val: number) => {
    const res = await api.updateDisasters({ intensity: val }, "primary");
    setPrimary(res.primary);
    setParallel(res.parallel);
  };

  const handleAction = async (
    action:
      | "deploy_emergency_response"
      | "toggle_emergency_response"
      | "activate_alternative_routes"
      | "toggle_alternative_routes"
      | "toggle_load_shedding"
      | "clear_road_blockages"
      | "reset",
    universeId = "primary"
  ) => {
    const res = await api.applyIntervention(universeId, action);
    setPrimary(res.primary);
    setParallel(res.parallel);
  };

  const handleTileClick = async (tile: TileState) => {
    if (viewMode !== "builder" && builderTool === "inspect") {
      // In command mode, clicking a road toggles a road blockage directly
      if (tile.tile_type === "road") {
        const res = await api.editTile({ x: tile.x, y: tile.y, toggle_block_road: true }, "primary");
        setPrimary(res.primary);
        setParallel(res.parallel);
      }
      return;
    }

    if (builderTool === "inspect") return;
    if (builderTool === "block_road") {
      const res = await api.editTile({ x: tile.x, y: tile.y, toggle_block_road: true }, "primary");
      setPrimary(res.primary);
      return;
    }
    if (builderTool === "ignite_fire") {
      const res = await api.editTile({ x: tile.x, y: tile.y, ignite_fire: true }, "primary");
      setPrimary(res.primary);
      return;
    }
    if (builderTool === "trigger_flood") {
      const res = await api.editTile({ x: tile.x, y: tile.y, trigger_flood: true }, "primary");
      setPrimary(res.primary);
      return;
    }

    const res = await api.editTile({ x: tile.x, y: tile.y, tile_type: builderTool }, "primary");
    setPrimary(res.primary);
  };

  const handleRewind = async (opts: { target_tick?: number; steps?: number }) => {
    const res = await api.rewind("primary", opts);
    setPrimary(res.primary);
    setParallel(res.parallel);
  };

  const handleSaveCity = async (name: string, description: string) => {
    await api.saveCity(name, description, "primary");
    const updatedCities = await api.listCities();
    setCities(updatedCities);
  };

  const overlays: { id: MapOverlayMode; label: string }[] = [
    { id: "standard", label: "City & Hazards" },
    { id: "congestion", label: "Traffic & Queues" },
    { id: "evacuation", label: "Dijkstra Evacuation" },
    { id: "power", label: "BFS/DFS Power Grid" },
  ];

  return (
    <div className="app-shell">
      <HeaderBar
        cityName={primary.city_name}
        tick={primary.tick}
        running={primary.running}
        speed={speed}
        wsConnected={wsConnected}
        viewMode={viewMode}
        cities={cities}
        onChangeView={setViewMode}
        onTogglePlay={handleTogglePlay}
        onStep={handleStep}
        onChangeSpeed={handleSpeedChange}
        onSelectCity={handleSelectCity}
      />

      {viewMode === "parallel" ? (
        <ParallelUniverseView
          parallel={parallel}
          overlayMode={overlayMode}
          onSyncFromPrimary={async () => {
            const res = await api.syncParallelFromPrimary();
            setParallel(res.parallel);
          }}
          onResetParallel={async () => {
            const res = await api.resetParallel();
            setParallel(res.parallel);
          }}
          onAction={(uid, action) => handleAction(action, uid)}
        />
      ) : viewMode === "analytics" ? (
        <CSInspectorPanel snapshot={primary} />
      ) : (
        <main className="workspace-grid">
          {viewMode === "builder" ? (
            <CityBuilderToolbar
              activeTool={builderTool}
              onSelectTool={setBuilderTool}
              onSaveCity={handleSaveCity}
            />
          ) : (
            <ControlPanel
              snapshot={primary}
              onToggleDisaster={handleToggleDisaster}
              onChangeIntensity={handleIntensity}
              onAction={(a) => handleAction(a, "primary")}
            />
          )}

          {/* Center Interactive Map + Time Machine */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div className="panel">
              <div className="canvas-toolbar">
                <div className="overlay-pills">
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, color: "#94a3b8", marginRight: 4 }}>
                    <Layers size={14} /> Overlay:
                  </span>
                  {overlays.map((ov) => (
                    <button
                      key={ov.id}
                      type="button"
                      className={`pill-btn ${overlayMode === ov.id ? "active" : ""}`}
                      onClick={() => setOverlayMode(ov.id)}
                    >
                      {ov.label}
                    </button>
                  ))}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <button
                    type="button"
                    className={`pill-btn ${use3D ? "active" : ""}`}
                    onClick={() => setUse3D((v) => !v)}
                  >
                    <Box size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
                    {use3D ? "3D Three.js Twin" : "Switch to 3D View"}
                  </button>
                </div>
              </div>

              {use3D ? (
                <CityView3D snapshot={primary} heightPx={460} />
              ) : (
                <CityCanvas2D
                  snapshot={primary}
                  overlayMode={overlayMode}
                  activeTool={viewMode === "builder" ? builderTool : "inspect"}
                  heightPx={460}
                  onTileClick={handleTileClick}
                />
              )}

              {/* Compact Map Legend */}
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 12,
                  marginTop: 9,
                  fontSize: 11,
                  color: "#94a3b8",
                }}
              >
                <span>🟦 Residential</span>
                <span>🟥 Hospital (+)</span>
                <span>🟪 School (S)</span>
                <span>🟨 Industry (I)</span>
                <span>🩵 Power Station (⚡)</span>
                <span>🟩 Shelter (E)</span>
                <span>⬜ Ambulance · 🟧 Fire Truck</span>
                <span style={{ marginLeft: "auto", color: "#64748b" }}>
                  Tip: Click any road tile in Command Mode to block/unblock it.
                </span>
              </div>
            </div>

            <TimeMachineBar snapshot={primary} onRewind={handleRewind} />
          </div>

          {/* Right Rail: AI Advisor + Live Event Telemetry */}
          <div className="right-rail" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <AIAdvisorPanel
              snapshot={primary}
              onExecuteAction={(actionKey) =>
                handleAction(
                  actionKey as
                    | "deploy_emergency_response"
                    | "activate_alternative_routes"
                    | "toggle_load_shedding"
                    | "clear_road_blockages",
                  "primary"
                )
              }
            />

            <section className="panel">
              <div className="panel-header" style={{ marginBottom: 8 }}>
                <h2 className="panel-title">
                  <Terminal size={14} color="#38bdf8" />
                  SimPy Event Stream
                </h2>
                <span className="mono" style={{ fontSize: 11, color: "#64748b" }}>
                  {primary.cs_metrics.simpy_events_processed} events
                </span>
              </div>
              <div className="event-feed mono">
                {[...primary.event_log].reverse().map((entry, idx) => (
                  <div key={`${idx}-${entry}`} className="event-item">
                    {entry}
                  </div>
                ))}
              </div>
            </section>
          </div>
        </main>
      )}
    </div>
  );
}
