# Proposal 3: Deterministic Kinematic Hierarchy (The "Controller" Pattern)

## 1. Synthesis & Goal

*   **From Proposal 2:** We accept the goal of **Predictable, Deterministic Movement**. The user does not want a physics sandbox. No bouncing, no sliding friction, no forces.
*   **From Critique 2:** We reject the idea of writing a custom collision solver in Python. We must leverage Pymunk's optimized spatial query engine without using its non-deterministic solver.

**The Solution:** A **Kinematic Character Controller** using **Shape Sweeps**.
We treat the Physics Engine effectively as a "Geometry Database". We query it to ask "Can I move here?", but we never let it move objects for us.

## 2. Core Mechanic: The Sweep-and-Slide

Instead of `Force -> Velocity -> Position` (Physics), we use `Input -> Desired Displacement -> Allowed Displacement -> Position`.

### 2.1 The Movement Logic
For every moving entity (Root):
1.  **Calculate Desired Vector:** `move_delta = velocity * dt`.
2.  **Shape Cast (Sweep):** Use `pymunk.Space.shape_query` (or a custom raycast bundle) to project the entity's shape forward along `move_delta`.
3.  **Detect Hit:** If the shape hits a "Wall" at distance `d < |move_delta|`:
    *   Move entity by `d - epsilon`.
    *   Project remaining velocity along the wall surface (Vector Projection).
    *   Repeat sweep with remaining distance (Max 2-3 iterations for corners).
4.  **Commit:** Manually set `body.position`.

This ensures:
*   **Zero Tunneling:** We sweep the shape, so we can't pass through thin walls.
*   **Absolute Control:** If the player stops input, the entity stops *instantly*. No friction sliding.
*   **Predictability:** The same input always yields the exact same position, regardless of "physics instability".

## 3. The Hierarchy: Rigid Locking

Since we have abandoned physics simulation, we can simplify the "Stacking" system to a pure Transform Hierarchy.

### 3.1 `Mount` Component
```python
@dataclass
class Mount(Component):
    parent_id: int = -1
    children_ids: List[int] = field(default_factory=list)
    mount_point_offset: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    layer_order: int = 0 # 1 = Above parent, -1 = Behind parent
```

### 3.2 The `HierarchySystem`
This system runs **after** the `KinematicMovementSystem`.

1.  **Topological Sort:** Ensure we process Parents before Children. (Or simply iterate recursively starting from Roots).
2.  **Teleport:**
    *   `Child.Position = Parent.Position + Parent.Rotation * Child.Offset`
    *   `Child.Velocity = Parent.Velocity` (For game logic queries, not movement).
3.  **Disable Collision:** Mounted children have their physics shapes **disabled** or set to `Sensor`. They do not interact with the world. The Parent is the only physical agent for the stack.

## 4. Handling Stacks & Interactions

### 4.1 "The Totem Pole"
If Entity A carries B, and B carries C:
*   A is the **Root**. A processes `Movement`.
*   A checks collisions against Walls.
*   B is locked to A. C is locked to B.
*   If A hits a wall, the whole stack stops.
*   **Bounding Box:** Optionally, A's collision shape can dynamically expand to encompass B and C, or we simply accept that "Riders don't have collision". Given the "Predictable" requirement, ignoring Rider collision is the cleanest, most arcade-like approach.

### 4.2 Dismounting
*   When B dismounts A:
    *   B's collision shape is re-enabled.
    *   B checks for overlap. If overlapping A, finding a near valid spot (Spiral Search) or just ejecting.

## 5. Implementation Roadmap

1.  **Engine Config:** Set Pymunk Space to have no gravity.
2.  **`KinematicSystem`:**
    *   Implement the `sweep_and_slide` function using Pymunk queries.
    *   Loop through all **Root** entities with `MovementController`.
    *   Apply logic.
3.  **`HierarchySystem`:**
    *   Implement recursive transform updates.
    *   Manage `shape.filter` to disable collisions for mounted units.

## 6. Why This Wins
*   **Meets User Request:** 100% Predictable. No "Sandbox" chaos.
*   **Robust:** Uses Pymunk's C-based collision detection (fast, accurate) without its solver (unstable).
*   **Clean:** Separates "Movement" (Roots) from "Attachment" (Children).
