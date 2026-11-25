# PARALLEL WORLD

### *Simulate. Decide. Survive.*

**Formal Title:** *Parallel World: An Intelligent Urban Digital Twin and Disaster Management Simulation Platform*

**Parallel World** is a real-time interactive urban disaster management simulator combining **SimCity-style city creation**, **graph & cellular-automata crisis propagation**, **intelligent emergency dispatch**, **Time Machine timeline branching**, and **simultaneous Parallel Universes (Universe A vs Universe B)** counterfactual comparison.

Instead of merely building a city, your mission as City Administrator is to **keep critical infrastructure, citizens, and traffic networks functioning during cascading emergencies**—and compare competing strategies side by side in real time.

---

## Core Features & Modules

1. **City Creation Engine**
   - Build and edit custom `20×14` urban grids with **Roads, Residential Blocks, Hospitals, Schools, Industries, Power Stations, Emergency Shelters, Green Parks, and Water Channels**.
   - Includes 3 curated city presets (*Metro Harbor District*, *Silicon Canal Grid*, *Frontier Sandbox*) and persistent custom city storage in **SQLite**.

2. **Disaster Simulation Engine**
   - **Cellular Automata (NumPy)** models dynamic hydrological **Flood** crest spread by tile elevation and **Urban Fire** thermal ignition/propagation.
   - **Discrete-Event Simulation (SimPy)** schedules seismic **Earthquake** aftershock pulses, **Road Blockages**, and infrastructure telemetry events.

3. **Intelligent Traffic Management**
   - **NetworkX** road network graph with congestion- & hazard-weighted edges.
   - **A\* Search** computes optimal vehicle detours around blocked/flooded corridors when alternative routing is activated.
   - **FIFO Intersection Queues (`collections.deque`)** simulate signal phases and intersection backlogs.

4. **Emergency Evacuation System**
   - **Priority Queue (`heapq`)** ranks emergencies by structural vulnerability, building criticality (hospitals & schools prioritized), and citizens at risk.
   - **Dijkstra's Algorithm** finds shortest safe evacuation routes from affected neighborhoods to available emergency shelters.

5. **Power Grid Simulator**
   - **BFS & DFS traversal** tracks energized connected subgrids and critical hospital/shelter reachability.
   - Models substation overloads and **cascading brownout trips**—mitigable with **Critical-First Load Shedding**.

6. **AI City Administrator**
   - Evaluates live telemetry to recommend ranked interventions with projected stability gains, citizens saved, and operational trade-offs.
   - Supports optional zero-cost **Ollama** local LLM enrichment (`http://localhost:11434`), seamlessly falling back to the deterministic tactical engine when offline.

7. **Time Machine**
   - **LIFO Stack** records full simulation snapshots at every tick.
   - Pause, undo 1 or 5 ticks, scrub the timeline, and **branch an alternate future** from an earlier decision point.

8. **Parallel Universes (Universe A vs Universe B)**
   - Run **two synchronized copies** of the exact same city & initial disaster seed simultaneously over WebSockets:
     - **Universe A:** Baseline / No emergency intervention
     - **Universe B:** Optimized emergency response (priority dispatch + A* alternative routes + load shedding)
   - Compare City Stability, Citizens Affected, Blocked Roads, Estimated Recovery Time, and live stability curves side by side.

9. **Dual 2D + 3D Visualization**
   - Primary 60fps interactive **PixiJS v8** 2D map with live overlays (*City & Hazards*, *Traffic & Queues*, *Dijkstra Evacuation*, *BFS/DFS Power Grid*).
   - Toggleable **Three.js** 3D Urban Digital Twin with extruded buildings, flood water planes, and live vehicles.

---

## Computer Science & DSA Architecture

| Concept | Application in Parallel World | Implementation |
| --- | --- | --- |
| **Graphs** | Weighted road network topology | [`backend/app/engine/graph_router.py`](backend/app/engine/graph_router.py) |
| **Dijkstra's Algorithm** | Shortest safe shelter evacuation routes | `RoadNetworkRouter.dijkstra_evacuation_routes` |
| **A\* Algorithm** | Congestion- & hazard-aware vehicle navigation | `RoadNetworkRouter.astar_path` |
| **BFS & DFS** | Power grid connected components & critical facility reachability | [`backend/app/engine/power_grid.py`](backend/app/engine/power_grid.py) |
| **Priority Queues** | Severity-ranked emergency dispatch (`heapq`) | [`backend/app/engine/evacuation.py`](backend/app/engine/evacuation.py) |
| **Queues** | Intersection traffic signal FIFO queues (`deque`) | `RoadNetworkRouter.update_traffic_queues` |
| **Stacks** | Time Machine undo, rewind & future branching | [`backend/app/engine/time_machine.py`](backend/app/engine/time_machine.py) |
| **Cellular Automata** | Flood & urban fire grid propagation (`NumPy`) | [`backend/app/engine/disasters.py`](backend/app/engine/disasters.py) |
| **Multi-Agent Systems** | Commuters, ambulances & fire trucks | [`backend/app/engine/simulation.py`](backend/app/engine/simulation.py) |
| **Discrete-Event Simulation** | Scheduled seismic pulses, disaster crests & telemetry (`SimPy`) | `DisasterEngine._schedule_simpy_event` |
| **Machine Learning** | Linear regression stability & recovery time prediction (`NumPy`) | [`backend/app/engine/ml_predictor.py`](backend/app/engine/ml_predictor.py) |
| **Databases** | Custom city blueprints & historical snapshots (`SQLite`) | [`backend/app/db/storage.py`](backend/app/db/storage.py) |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/DSA_CONCEPTS.md`](docs/DSA_CONCEPTS.md) for deep technical details.

---

## Technology Stack (100% Zero-Cost Local Stack)

- **Frontend:** React 18, TypeScript, Vite, **PixiJS v8** (2D visualization), **Three.js** (3D twin), Lucide Icons
- **Backend:** Python 3.13, **FastAPI**, **WebSockets**, **NetworkX**, **SimPy**, **NumPy**, **Pydantic**, **SQLite**
- **Optional Local AI:** **Ollama** (auto-detected on `localhost:11434`, offline-safe fallback)

---

## Quick Start

### 1. Backend (FastAPI + WebSocket Server)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (React + PixiJS + Three.js)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Vite automatically proxies `/api` and `/ws` requests to `http://127.0.0.1:8000`.

### Windows One-Command Launcher

```powershell
.\start.ps1
```

---

## Running Tests

```bash
cd backend
pytest -v
```

```bash
cd frontend
npm run build
```

---

## Disclaimer

*Parallel World is an interactive engineering and computer-science simulation platform designed for urban digital-twin experimentation and education, not an operational municipal disaster prediction tool.*
