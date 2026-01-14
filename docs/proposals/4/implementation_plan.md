# Implementation Plan: Proposal 4 - Hybrid Async HPA* Navigation

## 1. Problem Analysis
The current pathfinding system struggles with performance (frame spikes) and lacks robustness (entities getting stuck, no flight support). Proposal 4 suggests a Hybrid Async HPA* system with Steering Behaviors. This plan analyzes the technical options to implement this proposal and defines the roadmap.

## 2. Technical Solution Research & Ranking

### 2.1 Grid Data Storage
The grid needs to store `TraversalCapability` (bitmask) and `Cost` (float) for a potentially large map (e.g., 100x100 or larger).

*   **Option A: List of Lists (`List[List[NavNode]]`)**
    *   *Pros:* Native Python, easy to debug.
    *   *Cons:* High memory overhead per object, poor cache locality, slow iteration.
*   **Option B: Numpy Structured Array**
    *   *Pros:* Extremely fast bulk operations, contiguous memory, bitwise operations are vectorized.
    *   *Cons:* Dependency (already present in project).
*   **Option C: `array` module (Flat array)**
    *   *Pros:* Low memory, standard library.
    *   *Cons:* 1D indexing math required, no convenient bitwise vectorization.

**Ranking:**
1.  **Numpy Structured Array**: Best performance and convenient syntax for bitmasks.
2.  `array` module: Good fallback, but less expressive.
3.  List of Lists: Not suitable for scalable pathfinding.

**Decision:** Use **Numpy** (`np.uint8` for masks, `np.float32` for costs).

### 2.2 Pathfinding Core
We need to perform A* searches on the grid.

*   **Option A: `pathfinding` PyPI Library**
    *   *Pros:* Tested, ready to use.
    *   *Cons:* Generic implementation. Might be hard to optimize for our specific `TraversalCapability` bitmask logic without subclassing internals.
*   **Option B: Custom A* Implementation**
    *   *Pros:* Can be tightly optimized for our Numpy grid and Bitmask logic. We only need the core algorithm.
    *   *Cons:* Maintenance burden.
*   **Option C: `scipy.sparse.csgraph`**
    *   *Pros:* Very fast (C-backend).
    *   *Cons:* Overkill, requires constructing a graph matrix which is expensive for mutable grids.

**Ranking:**
1.  **Custom A* (Optimized)**: Essential for HPA* where we need specific control over "Entry Points" and Cluster refinement.
2.  `pathfinding` Library: Good for prototype, but potentially inflexible.
3.  `scipy`: Too heavy for dynamic grids.

**Decision:** Implement a **Custom A*** optimized for the HPA* Cluster structure.

### 2.3 Concurrency Model
Pathfinding must not block the main thread.

*   **Option A: `threading` (Shared Memory)**
    *   *Pros:* Simplest to implement. Direct access to the `NavigationGrid` (read-only during search). Low overhead for starting tasks.
    *   *Cons:* Subject to GIL. CPU-bound A* will still impact main thread if not careful (though pure Python operations release GIL less often).
*   **Option B: `multiprocessing` (True Parallelism)**
    *   *Pros:* Bypasses GIL completely. True background processing.
    *   *Cons:* High overhead to start/communicate. Requires serializing the Grid state or using complex `SharedMemory` buffers.
*   **Option C: `asyncio`**
    *   *Pros:* Cooperative multitasking.
    *   *Cons:* A* is CPU bound, so it blocks the event loop anyway. Not suitable.

**Ranking:**
1.  **`threading`**: Start here. HPA* is designed to be fast (<1ms per cluster search), so GIL contention should be minimal.
2.  `multiprocessing`: Reserve as a fallback if `threading` proves insufficient under load.

**Decision:** **Threading** with a `PriorityQueue`.

### 2.4 Movement / Steering
*   **Option A: Custom Kinematic Integration**
    *   *Pros:* Tight control, deterministic, "snappy" response. Code is simple (`velocity += force`).
    *   *Cons:* Must handle collision manually (Circle-Circle or Circle-Rect).
*   **Option B: Pymunk (Dynamic Physics)**
    *   *Pros:* Excellent collision resolution, rigid body dynamics.
    *   *Cons:* Can feel "floaty" or "sliding on ice" if friction isn't tuned perfectly. Overkill if we just want simple AI movement.
*   **Option C: `pygame.math` Vector2**
    *   *Pros:* Standard helper.
    *   *Cons:* Just a math class, still need integration logic.

**Ranking:**
1.  **Custom Kinematic Integration**: Yukkuri are soft/slow entities. Full rigid body physics is often frustrating for AI navigation. We want precise control.
2.  Pymunk: Use for *collision detection* only, or as a sensor, but drive movement kinematically.

**Decision:** **Custom Steering Forces** integrated with a simplified kinematic update, using Pymunk (or simple AABB) for collision resolution.

---

## 3. Implementation Plan

### Phase 1: Core Grid & HPA* Structure
- [ ] **Define Types**: `TraversalCapability` (IntFlag) and `TerrainType` (Enum).
- [ ] **NavigationGrid**: Implement using `numpy`. Properties: `cells` (w, h) array of structs.
- [ ] **Cluster System**: 
    - [ ] Divide grid into 8x8 blocks.
    - [ ] Implement `build_graph()`: Find entrances between clusters.
    - [ ] Implement `NavNode` mapping to Cluster Nodes.

### Phase 2: Async Service
- [ ] **NavigationService**: 
    - [ ] Setup `threading.Thread` daemon.
    - [ ] Input: `PriorityQueue` of `PathRequest`.
    - [ ] Output: `queue.Queue` of `PathResult`.
- [ ] **Worker Logic**:
    - [ ] Fetch request.
    - [ ] **Hierarchical Search**: Find path through Cluster Graph (Abstract Path).
    - [ ] **Local Refinement**: A* through specific nodes in the grid to connect cluster entrances.
    - [ ] **String Pulling**: Smooth the resulting coordinate list.
    - [ ] Push Result.

### Phase 3: Steering & Movement
- [ ] **SteeringComponent**: Add to ECS `velocity`, `max_speed`, `steering_forces`.
- [ ] **SteeringSystem**:
    - [ ] Calculate **Seek** force (target - pos).
    - [ ] Calculate **Separation** force (inverse square dist to neighbors).
    - [ ] Apply forces to velocity.
    - [ ] Update position.
- [ ] **Behavior Integration**: Update `MoveTo` node to request path, then let `SteeringSystem` follow the path.

### Phase 4: Integration & Optimization
- [ ] **Flight Support**: Pass `capabilities` mask to A*.
- [ ] **Stuck Detection**: Monitor velocity vs expected movement.
- [ ] **Visualization**: Draw green cluster boundaries, blue paths, red velocity vectors.
