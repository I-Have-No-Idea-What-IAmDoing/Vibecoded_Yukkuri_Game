# Proposal 4: Deterministic Kinematic Hierarchy (The "Controller" Pattern)

We treat the Physics Engine effectively as a "Geometry Database". We query it to ask "Can I move here?", but we never let it move objects for us.

## 2. Core Mechanic: The Sweep-and-Slide

Instead of `Force -> Velocity -> Position` (Physics), we use `Input -> Desired Displacement -> Allowed Displacement -> Position`.

**Crucial:** This logic must run on a **Fixed Timestep** (e.g., 60Hz) to ensure `dt` is constant, guaranteeing 100% determinism.

### 2.1 The Movement Logic
For every moving entity (Root):
1.  **Calculate Desired Vector:** `move_delta = velocity * fixed_dt`.
2.  **Broadphase Check:** Calculate the **Union AABB** of the Root and all attached Children. Use `pymunk.Space.bb_query` to find potential blockers.
    *   **Filtering:** Explicitly filter query results to include only "Obstacle" types (Walls, Floors).
3.  **Iterative Shape Cast (The "Sweep"):**
    *   Since Pymunk lacks a native "Sweep Shape" function, we approximate it:
    *   Check collision at the **Target Position** using the Root's shape AND all Children's shapes (effectively a compound check).
    *   If a collision is detected, perform a **Binary Search** along the `move_delta` vector to find the precise "Time of Impact" (TOI) where the shapes *just* touch the obstacle without overlapping.
    *   *Optimization:* For high speeds, perform intermediate checks (sub-stepping) to prevent tunneling through thin walls.
4.  **Resolve Collision:** If a hit occurs at fraction `t` (0 to 1):
    *   Move entity by `move_delta * (t - epsilon)`.
    *   **Slide:** Project the remaining velocity vector onto the wall's surface tangent.
    *   **Repeat:** Repeat the sweep with the new velocity vector (Max 3 iterations).
    *   If the entity is still stuck after max iterations, zero out the remaining velocity.
5.  **Commit:** Manually set `body.position`.

This ensures:
*   **Zero Tunneling:** Binary search/sub-stepping prevents passing through obstacles.
*   **Stack Awareness:** By checking child shapes, we prevent "Wide Riders" from clipping through walls.
*   **Absolute Control:** Immediate stops, no floaty physics.

## 3. The Hierarchy: Rigid Locking

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
    *   **Transform Change:** Position OR Rotation changed.
    *   **Structure Change:** Child added/removed.
2.  **Recursive Update:** Iterate recursively.
    *   `Child.Position = Parent.Position + Parent.Rotation * Child.Offset`
3.  **Collision Handling:**
    *   Mounted children convert their physical shapes to **Sensors**.
    *   They do not physically block movement (handled by the Root's compound check) but can detect overlaps (e.g., projectiles).

## 4. Handling Stacks & Interactions

### 4.1 "The Totem Pole" (Compound Collider)
If Entity A carries B:
*   A is the **Root**.
*   A's movement logic considers **A's Shape + B's Shape**.
*   If *any* shape in the stack hits a wall, the movement is blocked/slid.
*   **Head Check:** The compound check naturally covers "Head Checks" (B hitting ceiling) and "Side Checks" (B hitting wall).

### 4.2 Dismounting
*   **Voluntary Dismount:**
    *   B attempts to move to strict, deterministic relative offsets (1. Left, 2. Right, 3. Back).
    *   The first valid, non-colliding position is chosen.
    *   If all are blocked, the dismount **fails** (B stays mounted).
*   **Forced Dismount (e.g., A dies):**
    *   Attempt the standard deterministic dismount offsets.
    *   If all are blocked (B is trapped in walls/enemies):
        *   **CRUSH:** B takes massive damage or is instantly killed.
        *   Alternative: Emergency Eject to the Root's last valid position (if tracked).

## 5. Implementation Roadmap

1.  **Engine Config:** Set Pymunk Space to no gravity. Ensure **Fixed Timestep** loop.
2.  **`KinematicSystem`:**
    *   Implement `sweep_and_slide` using **Binary Search** for TOI.
    *   Implement **Compound Shape Checking** (Root + Children) during the sweep.
3.  **`HierarchySystem`:**
    *   Implement recursive transform updates.
    *   Manage `shape.sensor` toggling.
4.  **Dismount Logic:**
    *   Implement the "Try Offsets -> Fail/Crush" state machine.

## 6. Why This Wins
*   **True Determinism:** Fixed timestep + explicit resolution rules.
*   **Robust:** Compound collision checks prevent all clipping (Head/Side).
*   **Safe:** Handles forced dismounts gracefully (Crush mechanic) rather than undefined behavior.
