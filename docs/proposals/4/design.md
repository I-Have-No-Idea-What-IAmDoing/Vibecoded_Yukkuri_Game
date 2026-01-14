# Proposal 4: Hybrid Async HPA* with Steering Behaviors

## 1. Executive Summary

This proposal synthesizes the strengths of previous proposals to create a definitive navigation system for *Vibecoded Yukkuri Game*. It combines **Hierarchical Pathfinding (HPA*)** for scalable global navigation, **Asynchronous Processing** to eliminate frame spikes, and **Steering Behaviors** for fluid, organic movement and local avoidance.

**Key Features:**
- **Unified Grid:** Single grid using bitmasks for capability-based traversal (Walk, Fly, Swim).
- **Async HPA*:** Hierarchical A* running on a background worker thread.
- **Steering:** Physics-based movement (Seek, Separation, Avoidance) instead of grid snapping.
- **Reactive ECS:** Automatic grid updates based on entity component changes.

## 2. System Architecture

The architecture is divided into three distinct layers, ensuring separation of CPU-intensive pathfinding from the main game loop.

### Layer 1: The Unified Navigation Grid (Data Layer)
*Derived from Proposal 2 & 3*

Instead of maintaining separate grids for ground and air, we use a single grid where each node stores a `TraversalCapability` bitmask and a terrain cost.

#### Data Structures

```python
class TraversalCapability(IntFlag):
    WALK = 0x01    # Ground
    FLY = 0x02     # Air (ignores low obstacles)
    SWIM = 0x04    # Water
    
class TerrainType(Enum):
    ROAD = 0.5     # Preferred path
    GRASS = 1.0    # Standard
    MUD = 2.0      # Avoid unless necessary
    HAZARD = 10.0  # Soft avoidance
    
@dataclass(slots=True)
class NavNode:
    position: tuple[int, int]
    access_mask: TraversalCapability
    cost: float = 1.0  # Multiplier for G-score
```

- **HPA* Clusters:** The grid is virtually divided into 8x8 clusters.
- **Precomputed Edges:** Entry points between clusters are identified and distances pre-calculated.
- **Reactive Updates:** When an `Obstacle` component moves > `cell_size / 2` or changes state, only the specific nodes and the affected HPA* cluster are marked dirty.

### Layer 2: Asynchronous Pathplanner (Strategic Layer)
*Derived from Proposal 1 & 2*

Pathfinding is strictly prohibited on the main thread.

#### Workflow
1.  **Request:** Units submit `PathRequest` to a thread-safe `PriorityQueue`.
2.  **Process (Worker):**
    *   **Cache Check:** Key = `(start_cluster, end_cluster, capabilities)`.
    *   **Abstract Search:** Run A* on the Cluster Graph to find the sequence of clusters.
    *   **Refinement:** Run A* within each cluster to connect the entry/exit points.
    *   **Smoothing:** Run Funnel Algorithm (String Pulling) to remove jagged edges.
3.  **Result:** `PathResult` is pushed to a result queue for the main thread.

#### Data Structures

```python
@dataclass(order=True)
class PathRequest:
    priority: int
    timestamp: float
    entity_id: int
    start: tuple[int, int]
    end: tuple[int, int]
    capabilities: TraversalCapability
    
@dataclass
class PathResult:
    entity_id: int
    path: list[tuple[int, int]] # Smoothed world coordinates
    success: bool
    is_partial: bool
```

### Layer 3: Steering Controller (Operational Layer)
*Derived from Proposal 1*

Once a path is returned, the entity uses **Steering Behaviors** to follow it. This decoupling allows the path to be "stale" (calculated 100ms ago) while the movement remains fluid and responsive to immediate local threats.

#### Steering Formulas

1.  **Seek (Target):**
    ```python
    desired_velocity = normalize(target_pos - current_pos) * max_speed
    steering = desired_velocity - current_velocity
    ```
2.  **Arrival (Target, SlowRadius):**
    *   Same as Seek, but scales `desired_velocity` by `distance / slow_radius` when close.
3.  **Separation (Neighbors):**
    ```python
    force = Vector2(0, 0)
    for neighbor in neighbors:
        diff = current_pos - neighbor.pos
        force += normalize(diff) / length(diff) # Inverse square law
    ```
4.  **Integration:**
    ```python
    total_force = (seek * seek_weight) + (separation * sep_weight) + (avoid * avoid_weight)
    acceleration = clamp(total_force, max_force) / mass
    velocity = clamp(velocity + acceleration * dt, max_speed)
    position += velocity * dt
    ```

## 3. Workflow

1.  **Request:** `BehaviorTree` triggers `MoveTo(Target)`. `NavigationService` pushes request to Queue.
2.  **Process:** Worker Thread picks up request.
    *   Checks Cache.
    *   If miss, runs HPA* on Unified Grid.
    *   Runs String Pulling.
    *   Returns `Path` object via callback/future.
3.  **Receive:** Entity receives `Path`.
4.  **Execute:** `SteeringSystem` runs every frame on Main Thread:
    *   Calculates `Seek` force to next waypoint.
    *   Calculates `Separation` from neighbors.
    *   Updates velocity and position.

## 4. Technical Implementation Details

### 4.1 HPA* & Grid
We will implement a `ClusterGraph` class.
- **Edge Calculation:** For each pair of adjacent clusters, find "Entrances" (contiguous sequences of walkable nodes along the shared border). Place a graph node at the center of each entrance.
- **Inter-Cluster Edges:** Calculate the exact distance between Entrances within the same cluster using A*. Store this as the edge weight.
- **Refinement:** The algorithm first finds the path across clusters (low node count), then refines the path within clusters (small A*).
- **Optimization:** Pure Python A* is slow. HPA* minimizes the search depth, making Python performant enough.

### 4.2 Handling Flying Units
Flying units simply pass `TraversalCapability.FLY` (or `WALK | FLY`).
- **Low Obstacles:** Fences/small rocks block `WALK` but allow `FLY`.
- **High Obstacles:** Walls block both.
- The A* heuristic remains the same; only the `is_walkable` check changes to `(node.mask & entity_capability) > 0`.

### 4.3 Integration with Existing Systems
- **`NavigationService`:** Refactored to manage the worker thread and queues.
- **`MovementSystem`:** Currently direct position manipulation. Will be updated to apply velocity/forces based on Steering.
- **`Visual Debugger`:** Must be updated to draw the raw grid, cluster edges, and active paths for debugging.

## 5. Comparison to Alternatives

| Feature | Prop 1 (JPS) | Prop 2 (HPA*) | Prop 3 (Reactive) | **Prop 4 (Hybrid)** |
| :--- | :--- | :--- | :--- | :--- |
| **Algorithm** | JPS | HPA* | Theta* | **HPA*** |
| **Grid** | Sparse/Dense | Unified/Mask | Unified | **Unified/Mask** |
| **Async** | Yes | No (Planned) | Yes | **Yes** |
| **Movement** | Steering | Local Repair | Grid | **Steering** |
| **Dyn. Avoid**| Forces | Re-pathing | Re-pathing | **Forces** |

---

## 6. Advanced Features

### 6.1 Priority Queue for Path Requests
Not all path requests are equally urgent. A Yukkuri fleeing a predator needs a path *now*, while one wandering idly can wait.

- **Priority Levels:**
    - `CRITICAL` (0): Fleeing, under attack.
    - `HIGH` (1): Pursuing prey, seeking food when starving.
    - `NORMAL` (2): Standard movement (foraging, socializing).
    - `LOW` (3): Idle wandering.
- **Implementation:** Use a `queue.PriorityQueue` instead of a simple FIFO queue.

### 6.2 Timeout & Fallback Strategy
To prevent entities from freezing while waiting for a path:

- **Timeout:** Path requests have a configurable timeout (default: 500ms).
- **Fallback Behavior:**
    1.  If timeout expires, return a "beeline" path (direct vector to target).
    2.  The entity relies on its Steering Avoidance to navigate around obstacles locally.
    3.  If the direct path is completely blocked, return `FAILURE` to the Behavior Tree to trigger an alternative action (e.g., `Wander`).

### 6.3 Partial Path Returns
If the goal is completely unreachable (e.g., inside a walled-off area):

- **Strategy:** The pathfinder returns the path to the *closest reachable node* to the goal.
- **Signaling:** The `PathResult` object includes a `is_partial: bool` flag.
- **Benefit:** Entities can still move towards their target rather than standing idle, and the AI can decide whether to accept the partial path or try a different goal.

### 6.4 Stuck Detection & Anti-Jamming
Steering behaviors can occasionally lead to "jamming" (e.g., multiple entities wedged in a doorway).

- **Monitor:** Check if `velocity < 5.0` pixels/sec while `path_status == MOVING` for > 1.0 second.
- **Resolution Stages:**
    1.  **Stage 1 (Jitter):** Apply a random lateral force to break symmetry.
    2.  **Stage 2 (Shrink):** Temporarily reduce the entity's collision radius by 20% to squeeze through.
    3.  **Stage 3 (Force Repath):** Trigger a new path request with `ignore_dynamic_obstacles=True` for a short distance to push through the crowd.

### 6.5 Terrain Costs (Weighted Navigation)
To add gameplay depth, the grid supports variable movement costs.

- **Cost Modifiers:**
    - `ROAD`: 0.5 (Preferred path).
    - `GRASS`: 1.0 (Standard).
    - `MUD`: 2.0 (Avoid unless significant shortcut).
    - `HAZARD`: 10.0 (Soft avoidance, e.g., near predator nests).
- **Implementation:** The `NavNode` adds a `cost: float` field. The A* heuristic function accounts for these weights (`g_score + h_score`).

### 6.6 Update Optimization
To prevent excessive grid updates from tiny movements:
- **Threshold:** `Obstacle` components only mark the grid dirty if they move > `cell_size / 2` distance or change their `is_blocking` state.

---

## 7. Steering Tuning Parameters

Achieving fluid, natural movement requires careful tuning. The following parameters should be exposed for adjustment:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `max_speed` | 150.0 | Maximum velocity magnitude (pixels/sec). |
| `max_force` | 300.0 | Maximum steering force magnitude. |
| `mass` | 1.0 | Affects acceleration (`force / mass`). |
| `seek_weight` | 1.0 | Multiplier for the Seek behavior force. |
| `separation_weight` | 1.5 | Multiplier for the Separation behavior force. |
| `avoidance_weight` | 2.0 | Multiplier for the Obstacle Avoidance force. |
| `neighbor_radius` | 50.0 | Distance (pixels) to check for neighbors for Separation. |
| `lookahead_distance` | 75.0 | Distance (pixels) for obstacle avoidance raycasts. |
| `arrival_radius` | 25.0 | Distance to goal at which to start slowing down. |

These values should be stored per-entity-type (e.g., in `YukkuriTypeData`) to allow different species to have different movement feels (e.g., a small Reimu is nimble, a large predator is heavier).

---

## 8. Flight System Integration

The `TraversalCapability` must integrate cleanly with the existing `Flight` component and its states.

| `FlightState` | `TraversalCapability` | Notes |
| :--- | :--- | :--- |
| `GROUNDED` | `WALK` | Standard ground navigation. |
| `TAKING_OFF` | `WALK` | Still on ground, interruptible. |
| `AIRBORNE` | `FLY` | Ignores low obstacles. |
| `LANDING` | `FLY` | Transitioning, still in air layer. |
| `SWOOPING` | `WALK \| FLY` | Attack dive. *Can collide with both ground and air entities.* |

When a flying entity requests a path:
1.  The `NavigationService` reads the entity's current `FlightState`.
2.  It translates the state to the appropriate `TraversalCapability`.
3.  The path is calculated using the unified grid with the correct bitmask filter.

---

## 9. Anticipatory Caching (Path Prediction)

To further reduce perceived latency, paths can be precalculated for likely future actions.

- **Trigger:** When an entity enters an `IDLE` state.
- **Logic:**
    1.  Use the `UtilityAI` to identify the top 1-2 most likely next actions (e.g., `EatFood`, `SeekMate`).
    2.  Identify the target entity/position for those actions.
    3.  Submit a `LOW` priority `PathRequest` for those paths.
    4.  Store the results in the cache.
- **Benefit:** When the entity *actually* decides to pursue that action, the path is already available (cache hit), resulting in instant response.

---

## 10. Performance Verification

Success must be measurable. The following benchmarks define the performance targets for the new navigation system.

### 10.1 Targets

| Metric | Target | Measurement |
| :--- | :--- | :--- |
| **Avg. path time (50 entities)** | < 1.0 ms total | `profile_runner.py` |
| **Main-thread nav overhead** | < 0.5 ms/frame | `cProfile` / `py-spy` |
| **Frame-time spikes (nav-related)** | None > 5 ms | Manual testing + profiler |
| **Cache hit rate** | > 70% | Internal logging counter |
| **Memory (unified grid)** | < 1 MB | `tracemalloc` |

### 10.2 Verification Plan

1.  **Automated Benchmark:** Create a `test_navigation_benchmark.py` script that spawns 50 entities and issues simultaneous path requests, measuring total time.
2.  **Regression Test:** Add a performance assertion to CI: if median path time exceeds 2ms, fail the build.
3.  **Visual Debugging:** Ensure the `DebugRenderer` can toggle a view of:
    *   Cluster boundaries.
    *   Current paths (drawn as lines).
    *   Steering force vectors.
    *   Cache status per entity.

---

## 11. Lifecycle & State Management

### 11.1 Scene Transitions
When switching scenes (e.g., from Gameplay to Main Menu):
- **Action:** The `NavigationService` must `join()` or terminate its worker thread.
- **Cleanup:** Clear all pending `PathRequests` and flush the result queue to prevent memory leaks or processing for a destroyed world.

### 11.2 Save/Load System
- **Saving:**
    - The navigation grid itself does *not* need to submitted to the save file, as it is deterministically rebuilt from static level data + `Obstacle` components.
    - Active entities *should* serialize their `current_path_target` (if any).
- **Loading:**
    - On load, the `NavigationSystem` rebuilds the unified grid and clusters.
    - Entities are restored to `IDLE` or `WANDER` state initially. We do *not* attempt to restore the exact path progress, as the world state might have changed slightly.

---

## 12. Concurrency Strategy (GIL Mitigation)

Python's Global Interpreter Lock (GIL) poses a risk for CPU-bound tasks like A* even in a separate thread.

### 12.1 Primary Strategy: `threading` + Optimization
- We will initially use `threading.Thread` because it allows shared memory access to the `NavigationGrid`, avoiding complex serialization overhead.
- **Mitigation:**
    - The HPA* algorithm is efficient enough that individual path searches should be fast (< ms).
    - If a path search is taking too long (e.g., > 2ms), the worker can voluntarily `yield` or `sleep(0)` to allow the main thread to run.

### 12.2 Fallback Strategy: `multiprocessing`
- If profiling reveals that the worker thread is blocking the main loop due to the GIL:
    - We will switch to `multiprocessing.Process`.
    - **Trigger Condition:** Profile data shows `NavigationService._worker_loop` consuming > 5% of main-thread time (due to GIL contention) consistently over 60 frames.
    - **Trade-off:** This requires serializing the Grid state to the child process.
    - **Optimization:** Use `multiprocessing.shared_memory` to share the large grid array without copying.

---

## 13. Conclusion

Proposal 4 provides the **maximum robustness**. It uses HPA* for reliable global navigation, Bitmasks for flexible unit types, Async for performance, and Steering for quality of movement. The additions of priority handling, fallback strategies, explicit tuning parameters, and concrete performance benchmarks make it a complete, production-ready specification.
