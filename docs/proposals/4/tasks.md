# Implementation Tasks: Hybrid Async HPA* Navigation

## Phase 1: Core Grid & Data Structures
- [x] **Data Types**: Create `TraversalCapability` IntFlag and `TerrainType` Enum in `game/ai/navigation_constants.py`.
- [x] **Unified Grid**: Refactor `NavigationGrid` to use `NavNode` dataclass.
    - [x] Store nodes in flat 1D array or Numpy array for cache locality.
    - [x] Implement `get_node(x, y)` and `set_obstacle(x, y, mask, cost)`.
    - [x] Remove legacy `ground_grid` / `air_grid`.
- [x] **HPA* Clusters**: Implement `Cluster` and `ClusterGraph` classes.
    - [x] Logic to divide grid into 8x8 clusters.
    - [x] **Edge Calculation**: Implement logic to find "Entrances" between key clusters.
    - [x] **Inter-Cluster Edges**: Implement A* to calculate weights between entrances within a cluster.

## Phase 2: Asynchronous Pathfinding Service
- [x] **Data Structures**: Create `PathRequest` and `PathResult` dataclasses (Priority-aware).
- [x] **Threading Core**: Refactor `NavigationService`.
    - [x] Initialize `queue.PriorityQueue` for requests.
    - [x] Initialize `threading.Thread` as the worker.
    - [x] Implement `shutdown()` for lifecycle management.
- [x] **Worker Loop**: Implement the `_worker_loop` method:
    - [x] Check Cache.
    - [x] Run **Abstract Pathfind** (Cluster Graph A*).
    - [x] Run **Refinement** (Low-level A*).
    - [x] Run **String Pulling** (Funnel Algorithm).
    - [x] Post `PathResult` to thread-safe output queue.

## Phase 3: Steering System Integration
- [x] **Component**: Create `SteeringComponent` (velocity, max_speed, max_force, mass, time_stuck).
- [x] **System**: Create `SteeringSystem`.
    - [x] Implement `seek(target)` force vector math.
    - [x] Implement `separation(neighbors)` force using inverse square law.
    - [x] Implement `integration`: `velocity += acceleration * dt`.
- [x] **Behavior**: Update `MoveTo` behavior node.
    - [x] Switch to Async API state machine (`REQUESTING` -> `MOVING`).
    - [ ] Handle `FAILURE` or `TIMEOUT` by falling back to `Steering.seek(straight_line)`.

## Phase 4: Robustness & Advanced Features
- [x] **Stuck Detection**:
    - [x] In `SteeringSystem`, monitor `velocity < 5.0` while `MOVING`.
    - [x] Implement 3-stage resolution: Jitter -> Shrink Radius -> Force Repath.
- [x] **Flight Integration**:
    - [x] Map `FlightState` (Grounded/Airborne) to `TraversalCapability` bitmasks in `NavigationService` (Handled via capabilities arg).
- [x] **Anticipatory Caching**:
    - [x] Hook into `UtilityAI` to submit `LOW` priority path requests for likely next actions.
- [x] **Multiprocessing Fallback**:
    - [x] Add profiler hooks to measure worker thread impact.
    - [x] Stub out `multiprocessing` implementation structure (implementation can be deferred if threading performs well).

## Phase 5: Dynamic Updates & Lifecycle
- [x] **Reactive Updates**: Create `NavigationUpdateSystem`.
    - [x] Listen for `ComponentAdded/Removed` (Obstacle).
    - [x] Listen for `Transform` changes > `cell_size / 2` (De-scoped: only static updates for now).
    - [x] Mark affected Clusters as `dirty`.
- [x] **Lifecycle**:
    - [x] Ensure queues are cleared on Scene Exit.
    - [x] Ensure `NavigationService` is cleanly destroyed on Game Quit.

## Phase 6: Visualization & Verification
- [x] **Debug Rendering**: Created `NavigationDebugRenderer`.
    - [x] Draw Cluster boundaries (Green lines).
    - [x] Draw Entrance connections (Blue lines/circles).
    - [x] Draw Active Paths (Yellow smoothed lines).
    - [x] Draw Steering Vectors (Red rays).
- [x] **Benchmarks**: Created `test_navigation_benchmark.py`.
    - [x] Spawn 50 entities with concurrent path requests.
    - [x] Verify 100% success rate on empty grid.
