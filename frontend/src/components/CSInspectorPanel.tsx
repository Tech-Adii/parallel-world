import { Cpu } from "lucide-react";
import type { UniverseSnapshot } from "../types/simulation";

interface CSInspectorPanelProps {
  snapshot: UniverseSnapshot;
}

export function CSInspectorPanel({ snapshot }: CSInspectorPanelProps) {
  const cs = snapshot.cs_metrics;

  const concepts = [
    {
      concept: "Graphs (NetworkX)",
      application: "Road network topology & connectivity",
      liveValue: `${cs.graph_nodes} nodes · ${cs.graph_edges} edges`,
    },
    {
      concept: "Dijkstra's Algorithm",
      application: "Shortest safe shelter evacuation routes",
      liveValue: `${cs.dijkstra_routes_computed} active routes (avg cost ${cs.dijkstra_avg_cost})`,
    },
    {
      concept: "A* Search Algorithm",
      application: "Congestion-aware vehicle navigation",
      liveValue: `${cs.astar_paths_computed} paths (${cs.astar_nodes_expanded} expanded)`,
    },
    {
      concept: "BFS & DFS Traversal",
      application: "Power grid components & critical reachability",
      liveValue: `${cs.bfs_power_components} BFS grids · ${cs.dfs_critical_reachable} DFS critical`,
    },
    {
      concept: "Priority Queues (heapq)",
      application: "Severity-ranked emergency incident dispatch",
      liveValue: `${cs.priority_queue_size} queued · Top: ${cs.top_priority_incident}`,
    },
    {
      concept: "Queues (FIFO deque)",
      application: "Traffic signal intersection queues",
      liveValue: `${cs.traffic_queue_total} queued vehicles across intersections`,
    },
    {
      concept: "Stacks (LIFO)",
      application: "Time Machine undo, rewind & future branching",
      liveValue: `${cs.undo_stack_depth} snapshot frames stacked`,
    },
    {
      concept: "Cellular Automata (NumPy)",
      application: "Dynamic flood crest & urban fire propagation",
      liveValue: `${cs.ca_flood_cells} flood cells · ${cs.ca_fire_cells} fire cells`,
    },
    {
      concept: "Multi-Agent Systems",
      application: "Autonomous commuters, ambulances & fire trucks",
      liveValue: `${cs.multi_agent_count} active road agents`,
    },
    {
      concept: "Discrete-Event Simulation",
      application: "SimPy scheduled shocks, pulses & telemetry",
      liveValue: `${cs.simpy_events_processed} DES events @ t=${cs.simpy_sim_time}m`,
    },
    {
      concept: "Machine Learning (NumPy)",
      application: "Linear trend stability & recovery forecast",
      liveValue: `Next 5 ticks: ${cs.ml_predicted_stability_next}% · Rec: ${cs.ml_predicted_recovery_hours}h`,
    },
    {
      concept: "Databases (SQLite)",
      application: "Persistent city blueprints & simulation history",
      liveValue: `${cs.sqlite_saved_snapshots} historical checkpoints saved`,
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="panel">
        <div className="panel-header">
          <h2 className="panel-title">
            <Cpu size={15} color="#38bdf8" />
            Live Computer Science & DSA Engine Telemetry
          </h2>
          <span className="mono" style={{ fontSize: 12, color: "#94a3b8" }}>
            {snapshot.city_name} · T+{snapshot.tick}
          </span>
        </div>

        <div className="cs-grid">
          {concepts.map((item) => (
            <div key={item.concept} className="cs-card">
              <div style={{ fontSize: 13, fontWeight: 700, color: "#38bdf8", marginBottom: 4 }}>
                {item.concept}
              </div>
              <div style={{ fontSize: 11.5, color: "#94a3b8", marginBottom: 8 }}>{item.application}</div>
              <div
                className="mono"
                style={{
                  fontSize: 11.5,
                  color: "#e2e8f0",
                  padding: "5px 8px",
                  borderRadius: 6,
                  background: "rgba(15, 23, 42, 0.85)",
                  border: "1px solid rgba(56, 189, 248, 0.16)",
                }}
              >
                {item.liveValue}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Priority-Queue Emergency Dispatch Board</h3>
          <span className="mono" style={{ fontSize: 11.5, color: "#fda4af" }}>
            {snapshot.incidents.length} active incident(s)
          </span>
        </div>
        {snapshot.incidents.length === 0 ? (
          <div style={{ fontSize: 12.5, color: "#94a3b8" }}>No critical emergencies queued right now.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 8 }}>
            {snapshot.incidents.map((inc) => (
              <div
                key={inc.id}
                style={{
                  padding: "9px 11px",
                  borderRadius: 9,
                  background: "rgba(6, 10, 19, 0.72)",
                  border: "1px solid rgba(244, 63, 94, 0.25)",
                  fontSize: 12,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <strong style={{ color: "#fda4af" }}>
                    #{inc.priority_rank} {inc.kind}
                  </strong>
                  <span className="mono" style={{ color: "#fbbf24" }}>
                    Sev {inc.severity}
                  </span>
                </div>
                <div className="mono" style={{ fontSize: 11, color: "#94a3b8" }}>
                  Tile ({inc.x},{inc.y}) · At risk: {inc.citizens_at_risk} · Unit:{" "}
                  {inc.assigned_unit ?? "Awaiting dispatch"}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
