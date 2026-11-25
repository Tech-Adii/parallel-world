import type {
  AIAdviceResponse,
  CityPresetInfo,
  DisasterConfig,
  FullStateBundle,
  ParallelComparison,
  TileType,
  TimelineSummary,
  UniverseSnapshot,
} from "../types/simulation";

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API ${res.status}: ${errText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async getState(): Promise<FullStateBundle> {
    const res = await fetch("/api/state");
    if (!res.ok) throw new Error("Failed to fetch simulation state");
    return res.json();
  },

  async listCities(): Promise<CityPresetInfo[]> {
    const res = await fetch("/api/cities");
    if (!res.ok) throw new Error("Failed to fetch cities");
    return res.json();
  },

  play(scope: "all" | "primary" | "parallel" = "all") {
    return postJson("/api/simulation/play", { scope });
  },

  pause(scope: "all" | "primary" | "parallel" = "all") {
    return postJson("/api/simulation/pause", { scope });
  },

  step(universeId = "all") {
    return postJson<{ primary: UniverseSnapshot; parallel: ParallelComparison }>(
      `/api/simulation/step?universe_id=${encodeURIComponent(universeId)}`
    );
  },

  setSpeed(speed: number) {
    return postJson<{ speed: number }>("/api/simulation/speed", { speed });
  },

  updateDisasters(patch: Partial<DisasterConfig>, universeId = "primary") {
    return postJson<{ primary: UniverseSnapshot; parallel: ParallelComparison }>(
      `/api/simulation/disasters?universe_id=${encodeURIComponent(universeId)}`,
      patch
    );
  },

  applyIntervention(
    universeId: string,
    action:
      | "deploy_emergency_response"
      | "toggle_emergency_response"
      | "activate_alternative_routes"
      | "toggle_alternative_routes"
      | "toggle_load_shedding"
      | "clear_road_blockages"
      | "reset"
  ) {
    return postJson<{ primary: UniverseSnapshot; parallel: ParallelComparison }>(
      "/api/simulation/intervention",
      { universe_id: universeId, action }
    );
  },

  editTile(
    payload: {
      x: number;
      y: number;
      tile_type?: TileType;
      toggle_block_road?: boolean;
      ignite_fire?: boolean;
      trigger_flood?: boolean;
    },
    universeId = "primary"
  ) {
    return postJson<{ primary: UniverseSnapshot; parallel: ParallelComparison }>(
      `/api/simulation/tile?universe_id=${encodeURIComponent(universeId)}`,
      payload
    );
  },

  syncParallelFromPrimary() {
    return postJson<{ parallel: ParallelComparison }>("/api/parallel/sync");
  },

  resetParallel() {
    return postJson<{ parallel: ParallelComparison }>("/api/parallel/reset");
  },

  async getTimeline(universeId = "primary"): Promise<TimelineSummary> {
    const res = await fetch(`/api/timemachine/${encodeURIComponent(universeId)}`);
    if (!res.ok) throw new Error("Failed to load timeline");
    return res.json();
  },

  rewind(universeId: string, opts: { target_tick?: number; steps?: number }) {
    return postJson<{ rewound_to_tick: number; primary: UniverseSnapshot; parallel: ParallelComparison }>(
      "/api/timemachine/rewind",
      { universe_id: universeId, ...opts }
    );
  },

  getAIAdvice(universeId: string, question?: string) {
    return postJson<AIAdviceResponse>("/api/ai/advice", {
      universe_id: universeId,
      question: question || null,
    });
  },

  loadCity(cityId: string) {
    return postJson<{ primary: UniverseSnapshot; parallel: ParallelComparison }>(
      `/api/cities/load/${encodeURIComponent(cityId)}`
    );
  },

  saveCity(name: string, description: string, universeId = "primary") {
    return postJson<CityPresetInfo>("/api/cities/save", {
      name,
      description,
      universe_id: universeId,
    });
  },
};

export function createSimulationSocket(
  onMessage: (payload: {
    type: string;
    speed: number;
    primary: UniverseSnapshot;
    parallel: ParallelComparison;
  }) => void,
  onStatusChange: (connected: boolean) => void
): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/simulation`;
  const ws = new WebSocket(wsUrl);

  let pingTimer: number | undefined;
  ws.onopen = () => {
    onStatusChange(true);
    pingTimer = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 15000);
  };

  ws.onmessage = (event) => {
    if (event.data === "pong") return;
    try {
      const parsed = JSON.parse(event.data);
      if (parsed.type === "state_update") {
        onMessage(parsed);
      }
    } catch {
      // Ignore malformed frame
    }
  };

  ws.onclose = () => {
    onStatusChange(false);
    if (pingTimer) window.clearInterval(pingTimer);
  };

  ws.onerror = () => {
    onStatusChange(false);
  };

  return ws;
}
