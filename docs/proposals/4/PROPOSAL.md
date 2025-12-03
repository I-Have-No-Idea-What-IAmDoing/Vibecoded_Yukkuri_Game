# Proposal 4: Deterministic Kinematic Hierarchy (The "Controller" Pattern)

We treat the Physics Engine effectively as a "Geometry Database". We query it to ask "Can I move here?", but we never let it move objects for us.

## 2. Core Mechanic: The Sweep-and-Slide

Instead of `Force -> Velocity -> Position` (Physics), we use `Input -> Desired Displacement -> Allowed Displacement -> Position`.

### 2.1 The Movement Logic
For every moving entity (Root):
1.  **Calculate Desired Vector:** `move_delta = velocity * dt`.
2.  **Broadphase Check (Optimization):** Calculate the AABB of the path. Use `pymunk.Space.bb_query` to check for potential blockers.
    *   **Filtering:** Explicitly filter query results to include only "Obstacle" types (Walls, Floors). Ignore Triggers, Sensors, or other non-blocking entities.
    *   If the path is clear, move immediately and skip to step 5.
3.  **Hybrid Shape Sweep:**
    *   **Pymunk Limitation:** Pymunk does not support continuous shape sweeping natively.
    *   **Iterative Cast:** Perform `pymunk.Space.shape_query` at discrete steps along the path (e.g., every `radius/2` or `10px`).
    *   **Raycast Lead:** Perform a `segment_query` (Raycast) from the center to `target` to catch high-speed impacts, ensuring zero tunneling for the core.
    *   **Dynamic Bodies:** Currently treated as static Obstacles (Walls). If a player hits a movable crate, they stop.
4.  **Detect Hit:** If the shape hits a "Wall" at distance `d < |move_delta|`:
    *   Move entity by `d - epsilon` (to avoid overlap).
    *   Project remaining velocity along the wall surface (Vector Projection) to allow sliding.
    *   Repeat sweep with remaining distance (Max 1-2 iterations).
5.  **Commit:** Manually set `body.position`.

### 2.2 Collider Strategy
To solve "Ghost Collisions" (snagging on internal edges of tilemaps):
*   **Use Capsules:** Character colliders should be Capsules (or Circles) rather than Boxes. Rounded bottoms slide smoothly over the seams between adjacent floor tiles.
*   **Chamfered Boxes:** If Boxes are required, use "Chamfered" corners (octagons) to prevent corner snagging.

This ensures:
*   **High Performance:** Broadphase culling avoids expensive checks for the majority of frames.
*   **Zero Tunneling:** Hybrid Sweep prevents passing through thin walls.
*   **Absolute Control:** If the player stops input, the entity stops *instantly*. No friction sliding.
*   **Predictability:** The same input always yields the exact same position.

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

1.  **Dirty Flag Optimization:** Process the hierarchy for a Root if:
    *   It has moved (Position changed).
    *   It has rotated (Rotation changed).
    *   Its hierarchy structure has changed (Child added/removed).
2.  **Recursive Update:** Iterate recursively starting from the dirty Root to its children.
3.  **Teleport:**
    *   `Child.Position = Parent.Position + Parent.Rotation * Child.Offset`
    *   `Child.Velocity = Parent.Velocity` (For game logic queries).
4.  **Collision Handling:**
    *   Mounted children convert their physical shapes to **Sensors**.
    *   They do not physically block movement or push other objects.
    *   They *can* still detect overlaps (e.g., taking damage from a projectile).

## 4. Handling Stacks & Interactions

### 4.1 "The Totem Pole"
If Entity A carries B, and B carries C:
*   A is the **Root**. A processes `Movement`.
*   A checks collisions against Walls using its shape.
*   **Stack Collision Check:** To prevent riders from clipping through geometry, we perform a composite check.
    *   Before committing the move, iterate through **all** attached children (B, C).
    *   Check their shapes at the *target position*.
    *   If *any* child shape overlaps a Wall, the movement is blocked/resolved for the entire stack.
*   If A (or any rider) hits a wall/ceiling, the whole stack stops.

### 4.2 Dismounting
*   When B dismounts A:
    *   B attempts to move to strict, deterministic relative offsets (e.g., 1. Left, 2. Right, 3. Back).
    *   The first valid, non-colliding position is chosen.
    *   If all pre-defined spots are blocked, the dismount action **fails**.
    *   On success, B's collision shape is reverted from Sensor to Solid.

## 5. Implementation Roadmap

1.  **Engine Config:** Set Pymunk Space to have no gravity.
2.  **`KinematicSystem`:**
    *   Implement `sweep_and_slide` with **Broadphase** (filtered) and **Hybrid Shape Sweep**.
    *   Loop through all **active** Root entities with `MovementController`.
    *   Apply logic, including the **Stack Collision Check**.
3.  **`HierarchySystem`:**
    *   Implement recursive transform updates with robust dirty checking (Pos/Rot/Struct).
    *   Manage `shape.sensor` property to toggle collision modes for mounted units.

## 6. Why This Wins
*   **Meets User Request:** 100% Predictable. No "Sandbox" chaos.
*   **Robust:** Hybrid sweeps and Capsule shapes prevent tunneling and corner-catching issues.
*   **Gameplay Friendly:** Riders can still be hit (Sensors) and won't clip through ceilings (Stack Check).
*   **Clean:** Separates "Movement" (Roots) from "Attachment" (Children).
