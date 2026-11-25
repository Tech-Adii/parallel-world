# Computer Science & DSA Concepts Implemented

Every concept highlighted in the Parallel World design is implemented directly in production code and exposed live inside the **CS & DSA Telemetry** tab:

1. **Graphs (`NetworkX`)** — `backend/app/engine/graph_router.py`
   - Road tiles form an undirected weighted graph where edge weights dynamically reflect congestion, flood depth, fire hazard, and queue delay.
2. **Dijkstra's Algorithm** — `RoadNetworkRouter.dijkstra_evacuation_routes`
   - Computes shortest safe evacuation paths from affected residential/school/hospital zones to available emergency shelters with remaining capacity.
3. **A\* Algorithm** — `RoadNetworkRouter.astar_path`
   - Custom priority-queue A* with Manhattan heuristic navigates commuter and emergency vehicles around blocked and congested segments while tracking nodes expanded.
4. **BFS & DFS Traversal** — `PowerGridSimulator.step`
   - BFS counts distinct energized electrical subgrids; DFS verifies reachability of critical life-support facilities (hospitals & shelters).
5. **Priority Queues (`heapq`)** — `EvacuationDispatchEngine.evaluate_and_dispatch`
   - Ranks emergency incidents by structural vulnerability, building priority weight, and citizens at risk.
6. **Queues (`collections.deque`)** — `RoadNetworkRouter.update_traffic_queues`
   - FIFO queues model vehicle backlogs at intersections governed by adaptive or fixed signal phases.
7. **Stacks (LIFO)** — `TimeMachineStack` (`backend/app/engine/time_machine.py`)
   - Stores reversible simulation frames for 1-tick undo, multi-step rewind, and alternate-future timeline branching.
8. **Cellular Automata (`NumPy`)** — `DisasterEngine.step`
   - Vectorized grid matrices update Flood water depth and Urban Fire spread across neighbors each tick.
9. **Multi-Agent Systems** — `CitySimulation._step_vehicles`
   - Autonomous commuters, ambulances, fire trucks, and evacuation units react independently to road blockages and incidents.
10. **Discrete-Event Simulation (`SimPy`)** — `DisasterEngine._schedule_simpy_event`
    - Advances a SimPy simulation clock and executes scheduled seismic shockwaves, flood crest updates, and telemetry heartbeats.
11. **Machine Learning (`NumPy`)** — `TrafficAndRecoveryPredictor.predict`
    - Ordinary least-squares linear trend (`np.polyfit`) over recent stability windows forecasts 5-tick stability trajectory and recovery hours.
12. **Databases (`SQLite`)** — `SimulationDatabase` (`backend/app/db/storage.py`)
    - Persists user-created city blueprints and historical simulation checkpoints across sessions.
