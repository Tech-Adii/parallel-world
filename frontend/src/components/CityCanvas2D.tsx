import { useEffect, useRef, useState } from "react";
import { Application, Container, Graphics, Text } from "pixi.js";
import type { BuilderTool, MapOverlayMode, TileState, UniverseSnapshot } from "../types/simulation";

interface CityCanvas2DProps {
  snapshot: UniverseSnapshot;
  overlayMode: MapOverlayMode;
  activeTool?: BuilderTool;
  heightPx?: number;
  onTileClick?: (tile: TileState) => void;
}

const TILE_COLORS: Record<string, number> = {
  empty: 0x0e1726,
  water: 0x0b4f8a,
  road: 0x263246,
  residential: 0x3b82f6,
  hospital: 0xf43f5e,
  school: 0xa855f7,
  industry: 0xf59e0b,
  power_station: 0x06b6d4,
  shelter: 0x10b981,
  park: 0x15803d,
};

const TILE_GLYPHS: Record<string, string> = {
  hospital: "+",
  school: "S",
  power_station: "⚡",
  shelter: "E",
  industry: "I",
  residential: "R",
  park: "♣",
};

export function CityCanvas2D({
  snapshot,
  overlayMode,
  activeTool = "inspect",
  heightPx = 460,
  onTileClick,
}: CityCanvas2DProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const appRef = useRef<Application | null>(null);
  const worldLayerRef = useRef<Container | null>(null);
  const snapshotRef = useRef<UniverseSnapshot>(snapshot);
  const overlayRef = useRef<MapOverlayMode>(overlayMode);
  const onTileClickRef = useRef(onTileClick);

  const [hoveredTile, setHoveredTile] = useState<TileState | null>(null);
  const [ready, setReady] = useState(false);

  snapshotRef.current = snapshot;
  overlayRef.current = overlayMode;
  onTileClickRef.current = onTileClick;

  useEffect(() => {
    const containerEl = hostRef.current;
    if (!containerEl) return;

    let destroyed = false;
    const app = new Application();

    const initApp = async () => {
      const width = Math.max(320, containerEl.clientWidth || 720);
      await app.init({
        width,
        height: heightPx,
        backgroundColor: 0x070d19,
        antialias: true,
        resolution: Math.min(2, window.devicePixelRatio || 1),
        autoDensity: true,
      });

      if (destroyed) {
        app.destroy(true);
        return;
      }

      containerEl.innerHTML = "";
      containerEl.appendChild(app.canvas);
      app.canvas.style.width = "100%";
      app.canvas.style.height = `${heightPx}px`;
      app.canvas.style.display = "block";
      app.canvas.style.cursor = activeTool === "inspect" ? "pointer" : "crosshair";

      const world = new Container();
      app.stage.addChild(world);
      appRef.current = app;
      worldLayerRef.current = world;
      setReady(true);

      const handlePointerMove = (evt: PointerEvent) => {
        const snap = snapshotRef.current;
        const rect = app.canvas.getBoundingClientRect();
        const px = evt.clientX - rect.left;
        const py = evt.clientY - rect.top;
        const metrics = computeGridGeometry(rect.width, rect.height, snap.width, snap.height);
        const gx = Math.floor((px - metrics.offsetX) / metrics.cellSize);
        const gy = Math.floor((py - metrics.offsetY) / metrics.cellSize);
        if (gx >= 0 && gx < snap.width && gy >= 0 && gy < snap.height) {
          const tile = snap.tiles[gy * snap.width + gx] ?? null;
          setHoveredTile(tile);
        } else {
          setHoveredTile(null);
        }
      };

      const handlePointerLeave = () => setHoveredTile(null);

      const handleClick = (evt: MouseEvent) => {
        if (!onTileClickRef.current) return;
        const snap = snapshotRef.current;
        const rect = app.canvas.getBoundingClientRect();
        const px = evt.clientX - rect.left;
        const py = evt.clientY - rect.top;
        const metrics = computeGridGeometry(rect.width, rect.height, snap.width, snap.height);
        const gx = Math.floor((px - metrics.offsetX) / metrics.cellSize);
        const gy = Math.floor((py - metrics.offsetY) / metrics.cellSize);
        if (gx >= 0 && gx < snap.width && gy >= 0 && gy < snap.height) {
          const tile = snap.tiles[gy * snap.width + gx];
          if (tile) onTileClickRef.current(tile);
        }
      };

      app.canvas.addEventListener("pointermove", handlePointerMove);
      app.canvas.addEventListener("pointerleave", handlePointerLeave);
      app.canvas.addEventListener("click", handleClick);

      const ro = new ResizeObserver(() => {
        if (!hostRef.current || !appRef.current) return;
        const w = Math.max(320, hostRef.current.clientWidth);
        appRef.current.renderer.resize(w, heightPx);
        drawScene();
      });
      ro.observe(containerEl);

      return () => {
        ro.disconnect();
        app.canvas.removeEventListener("pointermove", handlePointerMove);
        app.canvas.removeEventListener("pointerleave", handlePointerLeave);
        app.canvas.removeEventListener("click", handleClick);
      };
    };

    let cleanupEvents: (() => void) | undefined;
    initApp().then((fn) => {
      cleanupEvents = fn;
    });

    return () => {
      destroyed = true;
      cleanupEvents?.();
      if (appRef.current) {
        appRef.current.destroy(true);
        appRef.current = null;
        worldLayerRef.current = null;
      }
      setReady(false);
    };
  }, [heightPx]);

  useEffect(() => {
    if (appRef.current?.canvas) {
      appRef.current.canvas.style.cursor = activeTool === "inspect" ? "pointer" : "crosshair";
    }
  }, [activeTool]);

  const drawScene = () => {
    const app = appRef.current;
    const world = worldLayerRef.current;
    if (!app || !world) return;

    const snap = snapshotRef.current;
    const overlay = overlayRef.current;
    const width = app.screen.width;
    const height = app.screen.height;
    const { cellSize, offsetX, offsetY } = computeGridGeometry(width, height, snap.width, snap.height);

    // Clear previous children safely
    const oldChildren = world.removeChildren();
    for (const c of oldChildren) {
      c.destroy();
    }

    const g = new Graphics();
    world.addChild(g);

    const pad = Math.max(1.5, cellSize * 0.06);

    // 1. Draw tiles
    for (const tile of snap.tiles) {
      const px = offsetX + tile.x * cellSize;
      const py = offsetY + tile.y * cellSize;
      const baseColor = TILE_COLORS[tile.tile_type] ?? 0x0e1726;

      // Dim unpowered structures in power overlay
      let alpha = 0.92;
      if (overlay === "power" && tile.tile_type !== "water" && tile.tile_type !== "empty" && !tile.powered) {
        alpha = 0.35;
      }

      if (tile.tile_type === "road") {
        // Road base
        let roadColor = 0x1e293b;
        if (tile.road_blocked) {
          roadColor = 0x7f1d1d;
        } else if (overlay === "congestion" || tile.congestion > 0.35) {
          if (tile.congestion > 0.72) roadColor = 0xdc2626;
          else if (tile.congestion > 0.42) roadColor = 0xd97706;
          else roadColor = 0x0f766e;
        } else if (tile.rerouted) {
          roadColor = 0x0e7490;
        }

        g.rect(px + 0.5, py + 0.5, cellSize - 1, cellSize - 1).fill({ color: roadColor, alpha });

        // Center road marking
        g.circle(px + cellSize / 2, py + cellSize / 2, Math.max(1.2, cellSize * 0.07)).fill({
          color: tile.powered ? 0x94a3b8 : 0x475569,
          alpha: 0.55,
        });

        // Blocked X marker
        if (tile.road_blocked) {
          const m = cellSize * 0.24;
          g.moveTo(px + m, py + m)
            .lineTo(px + cellSize - m, py + cellSize - m)
            .moveTo(px + cellSize - m, py + m)
            .lineTo(px + m, py + cellSize - m)
            .stroke({ width: 2.2, color: 0xfca5a5 });
        }

        // Queue indicator badge
        if (tile.queue_length > 0 && !tile.road_blocked) {
          g.circle(px + cellSize * 0.78, py + cellSize * 0.22, Math.max(2.5, cellSize * 0.14)).fill({
            color: 0xfbbf24,
            alpha: 0.95,
          });
        }
      } else {
        g.roundRect(px + pad, py + pad, cellSize - pad * 2, cellSize - pad * 2, Math.max(3, cellSize * 0.15)).fill({
          color: baseColor,
          alpha,
        });

        // Unpowered warning border
        if (!tile.powered && tile.power_load_mw > 0) {
          g.roundRect(px + pad, py + pad, cellSize - pad * 2, cellSize - pad * 2, Math.max(3, cellSize * 0.15)).stroke({
            width: 1.5,
            color: 0xef4444,
            alpha: 0.85,
          });
        }

        // Water shimmer line
        if (tile.tile_type === "water") {
          g.moveTo(px + cellSize * 0.2, py + cellSize * 0.5)
            .lineTo(px + cellSize * 0.8, py + cellSize * 0.5)
            .stroke({ width: 1.2, color: 0x38bdf8, alpha: 0.4 });
        }
      }

      // 2. Flood overlay (Cellular Automata water depth)
      if (tile.tile_type !== "water" && tile.flood_depth > 0.08) {
        g.rect(px + 1, py + 1, cellSize - 2, cellSize - 2).fill({
          color: 0x0284c7,
          alpha: Math.min(0.75, tile.flood_depth * 0.72),
        });
      }

      // 3. Fire overlay (Cellular Automata fire intensity)
      if (tile.fire_intensity > 0.08) {
        g.circle(px + cellSize * 0.5, py + cellSize * 0.5, cellSize * 0.36 * tile.fire_intensity + 3).fill({
          color: 0xf97316,
          alpha: 0.82,
        });
        g.circle(px + cellSize * 0.5, py + cellSize * 0.5, cellSize * 0.18).fill({
          color: 0xfef08a,
          alpha: 0.95,
        });
      }

      // 4. Glyph labels on special buildings (when cells are large enough)
      const glyph = TILE_GLYPHS[tile.tile_type];
      if (glyph && cellSize >= 18) {
        const label = new Text({
          text: glyph,
          style: {
            fontFamily: "Inter, sans-serif",
            fontSize: Math.max(9, Math.floor(cellSize * 0.42)),
            fontWeight: "700",
            fill: 0xffffff,
          },
        });
        label.anchor.set(0.5);
        label.x = px + cellSize / 2;
        label.y = py + cellSize / 2;
        world.addChild(label);
      }
    }

    // 5. Power Grid overlay links
    if (overlay === "power") {
      for (const link of snap.power_links) {
        const sx = offsetX + (link.source[0] + 0.5) * cellSize;
        const sy = offsetY + (link.source[1] + 0.5) * cellSize;
        const tx = offsetX + (link.target[0] + 0.5) * cellSize;
        const ty = offsetY + (link.target[1] + 0.5) * cellSize;
        g.moveTo(sx, sy)
          .lineTo(tx, ty)
          .stroke({
            width: link.powered ? 2 : 1.3,
            color: link.powered ? 0x38bdf8 : 0xf43f5e,
            alpha: link.powered ? 0.75 : 0.6,
          });
      }
    }

    // 6. Dijkstra Evacuation Routes overlay
    if (overlay === "evacuation" || snap.interventions.emergency_response_active) {
      const routeAlpha = overlay === "evacuation" ? 0.9 : 0.45;
      for (const route of snap.evacuation_routes.slice(0, 8)) {
        if (route.path.length < 2) continue;
        const first = route.path[0];
        g.moveTo(offsetX + (first[0] + 0.5) * cellSize, offsetY + (first[1] + 0.5) * cellSize);
        for (let i = 1; i < route.path.length; i++) {
          const pt = route.path[i];
          g.lineTo(offsetX + (pt[0] + 0.5) * cellSize, offsetY + (pt[1] + 0.5) * cellSize);
        }
        g.stroke({ width: overlay === "evacuation" ? 2.6 : 1.6, color: 0x34d399, alpha: routeAlpha });
      }
    }

    // 7. Priority Incident rings
    for (const inc of snap.incidents.slice(0, 5)) {
      const ix = offsetX + (inc.x + 0.5) * cellSize;
      const iy = offsetY + (inc.y + 0.5) * cellSize;
      g.circle(ix, iy, cellSize * 0.44).stroke({
        width: 2,
        color: inc.priority_rank === 1 ? 0xf43f5e : 0xfbbf24,
        alpha: 0.9,
      });
    }

    // 8. Multi-agent Vehicles (Commuters, Ambulances, Fire Trucks)
    for (const v of snap.vehicles) {
      const vx = offsetX + (v.x + 0.5) * cellSize;
      const vy = offsetY + (v.y + 0.5) * cellSize;
      let color = 0x38bdf8;
      let r = Math.max(2.5, cellSize * 0.14);
      if (v.kind === "ambulance") {
        color = 0xffffff;
        r = Math.max(3.2, cellSize * 0.18);
      } else if (v.kind === "fire_truck") {
        color = 0xf97316;
        r = Math.max(3.2, cellSize * 0.18);
      } else if (v.status === "queued") {
        color = 0xfbbf24;
      } else if (v.status === "rerouting") {
        color = 0x22d3ee;
      }
      g.circle(vx, vy, r).fill({ color, alpha: 0.96 });
      if (v.kind !== "commuter") {
        g.circle(vx, vy, r + 2.2).stroke({ width: 1.2, color: 0xf43f5e, alpha: 0.85 });
      }
    }
  };

  useEffect(() => {
    if (ready) {
      drawScene();
    }
  }, [ready, snapshot, overlayMode]);

  return (
    <div className="canvas-shell">
      <div ref={hostRef} style={{ width: "100%", height: `${heightPx}px` }} />
      {hoveredTile && (
        <div className="tile-tooltip mono">
          <span>
            ({hoveredTile.x},{hoveredTile.y}) <strong>{hoveredTile.tile_type.toUpperCase()}</strong>
          </span>
          <span>Elev: {hoveredTile.elevation.toFixed(1)}m</span>
          <span>Health: {hoveredTile.health.toFixed(0)}%</span>
          <span>Power: {hoveredTile.powered ? "ON" : "OUT"}</span>
          {hoveredTile.population > 0 && <span>Pop: {hoveredTile.population}</span>}
          {hoveredTile.capacity > 0 && (
            <span>
              Shelter: {hoveredTile.occupied}/{hoveredTile.capacity}
            </span>
          )}
          {hoveredTile.flood_depth > 0.05 && (
            <span style={{ color: "#38bdf8" }}>Flood: {(hoveredTile.flood_depth * 100).toFixed(0)}%</span>
          )}
          {hoveredTile.fire_intensity > 0.05 && (
            <span style={{ color: "#fb923c" }}>Fire: {(hoveredTile.fire_intensity * 100).toFixed(0)}%</span>
          )}
          {hoveredTile.tile_type === "road" && (
            <span>
              {hoveredTile.road_blocked
                ? "BLOCKED"
                : `Cong: ${(hoveredTile.congestion * 100).toFixed(0)}% | Q: ${hoveredTile.queue_length}`}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function computeGridGeometry(width: number, height: number, cols: number, rows: number) {
  const pad = 12;
  const availW = Math.max(100, width - pad * 2);
  const availH = Math.max(100, height - pad * 2);
  const cellSize = Math.floor(Math.min(availW / cols, availH / rows));
  const gridW = cellSize * cols;
  const gridH = cellSize * rows;
  const offsetX = Math.floor((width - gridW) / 2);
  const offsetY = Math.floor((height - gridH) / 2);
  return { cellSize, offsetX, offsetY };
}
