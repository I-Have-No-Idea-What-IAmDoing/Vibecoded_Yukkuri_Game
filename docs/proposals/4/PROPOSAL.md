# Proposal 4: Deterministic Kinematic Hierarchy (The "Controller" Pattern)

We treat the Physics Engine effectively as a "Geometry Database". We query it to ask "Can I move here?", but we never let it move objects for us.

## 2. Core Mechanic: The Sweep-and-Slide

Instead of `Force -> Velocity -> Position` (Physics), we use `Input -> Desired Displacement -> Allowed Displacement -> Position`.

### 2.1 The Movement Logic
For every moving entity (Root):
1.  **Calculate Desired Vector:** `move_delta = velocity * dt`.
2.  **Broadphase Check (Optimization):** Calculate the AABB of the path. Use `pymunk.Space.bb_query` to check for potential blockers. If the path is clear, move immediately and skip to step 5.
3.  **Raycast Bundle (Sweep):** Use `pymunk.Space.segment_query` to cast rays from the entity's leading corners and center along `move_delta`. This is significantly faster than full shape queries and prevents tunneling.
4.  **Detect Hit:** If a ray hits a "Wall" at distance `d < |move_delta|`:
    *   Move entity by `d - epsilon`.
    *   Project remaining velocity along the wall surface (Vector Projection).
    *   Repeat sweep with remaining distance (Max 1-2 iterations).
5.  **Commit:** Manually set `body.position`.

This ensures:
*   **High Performance:** Broadphase culling avoids expensive checks for the majority of frames (moving through empty space).
*   **Zero Tunneling:** We sweep the path, so we can't pass through thin walls.
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

1.  **Dirty Flag Optimization:** Only process the hierarchy for a Root if it has successfully moved this frame. Static stacks require no updates.
2.  **Recursive Update:** Iterate recursively starting from the moved Root to its children.
3.  **Teleport:**
    *   `Child.Position = Parent.Position + Parent.Rotation * Child.Offset`
    *   `Child.Velocity = Parent.Velocity` (For game logic queries, not movement).
4.  **Disable Collision:** Mounted children have their physics shapes **disabled** or set to `Sensor`. They do not interact with the world. The Parent is the only physical agent for the stack.

## 4. Handling Stacks & Interactions

### 4.1 "The Totem Pole"
If Entity A carries B, and B carries C:
*   A is the **Root**. A processes `Movement`.
*   A checks collisions against Walls.
*   B is locked to A. C is locked to B.
*   If A hits a wall, the whole stack stops.
*   **Bounding Box:** A's collision shape can optionally expand, but for performance, we generally accept that "Riders don't have collision".

### 4.2 Dismounting
*   When B dismounts A:
    *   B's collision shape is re-enabled.
    *   B checks for overlap. If overlapping A, finding a near valid spot (Spiral Search) or just ejecting.

## 5. Implementation Roadmap

1.  **Engine Config:** Set Pymunk Space to have no gravity.
2.  **`KinematicSystem`:**
    *   Implement `sweep_and_slide` with **Broadphase** and **Raycast** optimizations.
    *   Loop through all **active** Root entities with `MovementController`.
    *   Apply logic.
3.  **`HierarchySystem`:**
    *   Implement recursive transform updates with dirty checking.
    *   Manage `shape.filter` to disable collisions for mounted units.

## 6. Why This Wins
*   **Meets User Request:** 100% Predictable. No "Sandbox" chaos.
*   **Performant:** Minimizes expensive physics queries and eliminates redundant transform updates.
*   **Clean:** Separates "Movement" (Roots) from "Attachment" (Children).
