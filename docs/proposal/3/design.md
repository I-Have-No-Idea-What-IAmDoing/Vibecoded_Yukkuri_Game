# Movement System Overhaul Design Proposal

## 1. Introduction & Rationale

### Current System Limitations
The current movement system for Yukkuris is primarily implemented within the `MoveToTarget` behavior tree action (`src/yukkuri_game/game/ai/behavior.py`). This imperative approach has several drawbacks:

1.  **Tight Coupling**: The behavior tree node handles pathfinding, path following, raycasting for smoothing, stuck detection, and velocity application. This violates the Single Responsibility Principle.
2.  **Lack of Local Avoidance**: There is no robust system for avoiding dynamic obstacles (other Yukkuris). The current system relies on basic physics collisions (using Pymunk) or static grid updates, leading to "clumping" or getting stuck on each other.
3.  **Rigid Movement**: The movement is purely functional (move from A to B). It lacks expressiveness (e.g., hopping, dragging feet when tired, running vs walking) derived from the entity's state.
4.  **Performance bottlenecks**: Recalculating paths and performing raycasts inside the behavior tree update loop (even with timers) can be inefficient if many entities are active.

### Goals of the Overhaul
1.  **Decoupling**: Separate high-level intent ("Go to the kitchen") from low-level execution (avoiding the chair, steering around a sibling, applying physics forces).
2.  **Robust Local Avoidance**: Implement steering behaviors (Context-Based Steering or Boids-like separation) to allow Yukkuris to flow around each other naturally.
3.  **Expressive Locomotion**: Introduce a "Locomotion" layer that translates movement velocity into character-specific physics impulses (hops, slides) and syncs with animations.
4.  **ECS-Native**: Move state and logic out of Python classes/Behavior Trees and into ECS Components and Systems.

---

## 2. Proposed Architecture

The new architecture splits the movement responsibilities into three distinct layers:

1.  **Navigation Layer (High Level)**: Calculates the route (Pathfinding).
2.  **Steering Layer (Mid Level)**: Calculates immediate desired velocity based on the path and local environment (Steering Behaviors).
3.  **Locomotion Layer (Low Level)**: Applies physical forces to the body to achieve the desired velocity (Physics/Animation).

### 2.1 Components

We will introduce the following new/refactored components:

#### `MovementTarget`
Represents the **Intent** of the agent.
```python
@dataclass
class MovementTarget:
    target_pos: Tuple[float, float] # The final destination
    path: List[Tuple[float, float]] # The A* path
    current_waypoint_index: int = 0
    tolerance: float = 10.0 # How close is "arrived"?
```

#### `SteeringAgent`
Configuration for the steering algorithms.
```python
@dataclass
class SteeringAgent:
    max_speed: float = 100.0
    max_force: float = 500.0 # Limit on how fast we can turn/accelerate
    mass: float = 1.0
    radius: float = 30.0 # For collision avoidance

    # Behavior Weights
    weight_seek: float = 1.0
    weight_avoid: float = 2.0
    weight_separate: float = 1.5
    weight_align: float = 0.5
```

#### `LocomotionState` (Optional/Future)
Defines the style of movement.
```python
@dataclass
class LocomotionState:
    gait_type: str = "crawl" # crawl, hop, run
    hop_timer: float = 0.0
```

### 2.2 Systems

#### `NavigationSystem`
*   **Responsibility**: Asynchronous pathfinding.
*   **Input**: Entities with `MovementTarget` where `path` is empty/stale but `target_pos` is set.
*   **Action**: Calls `NavigationService` (A*) to fill `MovementTarget.path`. Supports partial paths and re-pathing on failure.

#### `SteeringSystem`
*   **Responsibility**: Calculating the `desired_velocity`.
*   **Input**: `Transform`, `MovementTarget`, `SteeringAgent`, `PhysicsBody` (neighbors).
*   **Logic**:
    1.  **Path Following**: Determine the current target waypoint from `MovementTarget`. Calculate a `Seek` force towards it.
    2.  **Separation**: Query nearby entities (spatial hash/quadtree or Pymunk queries). Calculate a `Repulsion` force to maintain personal space.
    3.  **Obstacle Avoidance**: Raycast ahead. If an obstacle is detected, calculate an `Avoid` force (lateral to the obstacle).
    4.  **Summation**: Sum all weighted forces, clamp to `max_force`, add to current velocity, clamp to `max_speed`.
    5.  **Output**: Store this result as a "desired velocity" vector (or apply directly if using simplified physics).

#### `LocomotionSystem`
*   **Responsibility**: Translating `desired_velocity` into Pymunk forces.
*   **Input**: `PhysicsBody`, `SteeringAgent` (calculated velocity).
*   **Logic**:
    *   Instead of setting `body.velocity` directly (which breaks physics interactions), apply forces/impulses.
    *   **Gait Logic**: If "Hopping", apply impulse only when on ground (timer based). If "Sliding", apply constant force.
    *   Syncs `Transform` rotation to velocity direction (with smoothing).

### 2.3 Behavior Tree Integration

The `MoveToTarget` action node becomes significantly simpler. It acts as a **Supervisor**.

*   **Initialize**: Set `MovementTarget` component on the entity with the destination.
*   **Update**:
    *   Check `MovementTarget` status (Has arrived? Path failed?).
    *   Return `RUNNING` while moving.
    *   Return `SUCCESS` when `dist(pos, target) < tolerance`.
    *   Return `FAILURE` if stuck or unreachable.
*   **Terminate**: Remove `MovementTarget` component (or clear it).

---

## 3. Detailed Logic

### Steering Behaviors

We will use a **Weighted Truncated Sum** approach.

$$ Force_{total} = (Force_{seek} * W_{seek}) + (Force_{separate} * W_{separate}) + (Force_{avoid} * W_{avoid}) $$

1.  **Seek**: $TargetPos - CurrentPos$ (Normalized * MaxSpeed).
2.  **Separation**: For each neighbor within radius $R$: $\sum \frac{CurrentPos - NeighborPos}{Distance^2}$.
3.  **Obstacle Avoidance**: Raycast along velocity vector. If hit, force is perpendicular to normal.

### Handling "Stuck" State
The `SteeringSystem` can detect if `desired_velocity` is high but `actual_velocity` is low for a prolonged period.
*   **Reaction**: Trigger a "Stuck" flag on the `MovementTarget`.
*   **BT Reaction**: The `MoveToTarget` node sees the flag, returns `FAILURE` (or attempts a jump/wiggle), prompting the Utility AI to pick a new goal or retry.

### Dynamic Obstacles
By using `Separation` steering, Yukkuris will naturally push apart. For larger entities (Player, furniture), `Obstacle Avoidance` (Raycasting) is preferred.

---

## 4. Benefits Summary

| Feature | Old System | New System |
| :--- | :--- | :--- |
| **Control** | Imperative (Move Node does everything) | Data-Driven (Systems process Components) |
| **Crowds** | Overlap/Physics Jitter | Smooth Flow/Separation |
| **Physics** | Direct Velocity Setting | Force/Impulse based (Natural interactions) |
| **Extensibility** | Hard to add new movement types | Easy (Add new Gait in LocomotionSystem) |
| **Debug** | Hard (Logic hidden in BT) | Easy (Visualize forces in SteeringSystem) |
