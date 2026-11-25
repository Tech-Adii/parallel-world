import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { UniverseSnapshot } from "../types/simulation";

interface CityView3DProps {
  snapshot: UniverseSnapshot;
  heightPx?: number;
}

const BUILDING_COLORS: Record<string, number> = {
  empty: 0x0f172a,
  water: 0x0284c7,
  road: 0x1e293b,
  residential: 0x3b82f6,
  hospital: 0xf43f5e,
  school: 0xa855f7,
  industry: 0xf59e0b,
  power_station: 0x06b6d4,
  shelter: 0x10b981,
  park: 0x16a34a,
};

const BUILDING_HEIGHTS: Record<string, number> = {
  empty: 0.08,
  water: 0.04,
  road: 0.1,
  park: 0.2,
  residential: 0.95,
  school: 0.7,
  shelter: 0.65,
  industry: 1.1,
  hospital: 1.35,
  power_station: 1.25,
};

export function CityView3D({ snapshot, heightPx = 460 }: CityView3DProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cityGroupRef = useRef<THREE.Group | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const width = Math.max(320, el.clientWidth || 720);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060b16);
    scene.fog = new THREE.FogExp2(0x060b16, 0.025);

    const camera = new THREE.PerspectiveCamera(45, width / heightPx, 0.1, 120);
    camera.position.set(14, 15, 18);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, heightPx);
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    el.innerHTML = "";
    el.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.maxPolarAngle = Math.PI * 0.46;

    const ambient = new THREE.AmbientLight(0xcbd5e1, 0.7);
    scene.add(ambient);

    const dirLight = new THREE.DirectionalLight(0x7dd3fc, 1.35);
    dirLight.position.set(12, 22, 10);
    scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(0x6366f1, 0.55);
    rimLight.position.set(-14, 10, -12);
    scene.add(rimLight);

    const gridHelper = new THREE.GridHelper(24, 24, 0x1e293b, 0x0f172a);
    gridHelper.position.y = -0.02;
    scene.add(gridHelper);

    const cityGroup = new THREE.Group();
    scene.add(cityGroup);
    cityGroupRef.current = cityGroup;

    let animId = 0;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const ro = new ResizeObserver(() => {
      if (!containerRef.current || !rendererRef.current) return;
      const w = Math.max(320, containerRef.current.clientWidth);
      camera.aspect = w / heightPx;
      camera.updateProjectionMatrix();
      rendererRef.current.setSize(w, heightPx);
    });
    ro.observe(el);

    return () => {
      cancelAnimationFrame(animId);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      rendererRef.current = null;
      cityGroupRef.current = null;
    };
  }, [heightPx]);

  useEffect(() => {
    const group = cityGroupRef.current;
    if (!group) return;

    while (group.children.length > 0) {
      const obj = group.children[0] as THREE.Mesh;
      group.remove(obj);
      obj.geometry?.dispose();
      if (Array.isArray(obj.material)) {
        obj.material.forEach((m) => m.dispose());
      } else {
        obj.material?.dispose();
      }
    }

    const ox = -snapshot.width / 2 + 0.5;
    const oz = -snapshot.height / 2 + 0.5;
    const unitGeo = new THREE.BoxGeometry(0.84, 1, 0.84);

    for (const tile of snapshot.tiles) {
      const h = BUILDING_HEIGHTS[tile.tile_type] ?? 0.1;
      let color = BUILDING_COLORS[tile.tile_type] ?? 0x1e293b;
      if (tile.tile_type === "road" && tile.road_blocked) {
        color = 0x991b1b;
      }

      const mat = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.45,
        metalness: 0.25,
        emissive: tile.fire_intensity > 0.1 ? new THREE.Color(0xf97316) : new THREE.Color(0x000000),
        emissiveIntensity: tile.fire_intensity > 0.1 ? 0.75 : 0,
        opacity: tile.powered || tile.tile_type === "water" ? 1.0 : 0.45,
        transparent: !tile.powered && tile.tile_type !== "water",
      });

      const mesh = new THREE.Mesh(unitGeo, mat);
      mesh.scale.y = h;
      mesh.position.set(ox + tile.x, h / 2, oz + tile.y);
      group.add(mesh);

      if (tile.tile_type !== "water" && tile.flood_depth > 0.12) {
        const floodMat = new THREE.MeshStandardMaterial({
          color: 0x0ea5e9,
          transparent: true,
          opacity: Math.min(0.68, tile.flood_depth * 0.7),
        });
        const floodMesh = new THREE.Mesh(unitGeo, floodMat);
        const fh = 0.16 + tile.flood_depth * 0.35;
        floodMesh.scale.set(1.08, fh, 1.08);
        floodMesh.position.set(ox + tile.x, fh / 2, oz + tile.y);
        group.add(floodMesh);
      }
    }

    const vGeo = new THREE.BoxGeometry(0.32, 0.22, 0.32);
    for (const v of snapshot.vehicles) {
      const vColor = v.kind === "ambulance" ? 0xffffff : v.kind === "fire_truck" ? 0xf97316 : 0x38bdf8;
      const vMat = new THREE.MeshStandardMaterial({ color: vColor, emissive: vColor, emissiveIntensity: 0.4 });
      const vm = new THREE.Mesh(vGeo, vMat);
      vm.position.set(ox + v.x, 0.24, oz + v.y);
      group.add(vm);
    }
  }, [snapshot]);

  return (
    <div className="canvas-shell">
      <div ref={containerRef} style={{ width: "100%", height: `${heightPx}px` }} />
      <div className="tile-tooltip mono">
        <span>3D Urban Digital Twin (Three.js) — Drag to orbit · Scroll to zoom</span>
      </div>
    </div>
  );
}
