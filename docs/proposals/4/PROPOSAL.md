# Proposal 4: Deterministic Kinematic Hierarchy (The "Controller" Pattern)

We treat the Physics Engine effectively as a "Geometry Database". We query it to ask "Can I move here?", but we never let it move objects for us.

## 2. Core Mechanic: The Sweep-and-Slide

Instead of `Force -> Velocity -> Position` (Physics), we use `Input -> Desired Displacement -> Allowed Displacement -> Position`.

**Crucial:** This logic must run on a **Fixed Timestep** (e.g., 60Hz) to ensure `dt` is constant, guaranteeing 100% determinism.

### 2.1 The Movement Logic
For every moving entity (Root):
1.  **Calculate Desired Vector:** `move_delta = velocity * fixed_dt`.
2.  **The Sweep (Capsule Cast):**
    *   Use `pymunk.Space.segment_query(start, end, radius, filter)` to detect the **First Impact**.
    *   **Radius:** Use the Root entity's collision radius. This effectively performs a "Circle Sweep" or "Capsule Cast", ensuring **Zero Tunneling**.
    *   **Filter:** Exclude Sensors and the entity's own shapes.
3.  **Resolve Collision:**
    *   If the query returns a hit at fraction `alpha` (0 to 1):
        *   The safe movement is `move_delta * (alpha - epsilon)`.
        *   **Slide:** Calculate the remainder vector (`move_delta * (1-alpha)`). Project this vector onto the wall's surface tangent (using the `normal` returned by the query).
        *   **Repeat:** Perform a second sweep with the projected "slide" vector. (Max 3 iterations).
    *   If no hit: Move the full `move_delta`.
4.  **Commit:** Manually set `body.position`.

### 2.2 Why `segment_query`?
*   **Performance:** It is a native C function in Chipmunk/Pymunk.
*   **Correctness:** It checks the continuous volume between start and end, preventing "bullet through paper" tunneling.
*   **Simplicity:** It returns the exact surface normal and impact point, making "Sliding" math trivial.

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
    *   They do not physically block movement (handled by the Root's Sweep) but can detect overlaps (e.g., projectiles).

## 4. Handling Stacks & Interactions

### 4.1 "The Totem Pole" (Compound Collider)
When entities are stacked, the Root entity assumes responsibility for the movement of the whole stack.
*   **Movement Collider:** The Root uses a **Bounding Capsule** or **Circle** that encompasses the stack for the purpose of environmental collision (Walls/Floor).
    *   *Simplification:* We assume the stack moves as one unit. The Root's radius is usually sufficient for width.
*   **Head/Ceiling Checks:** If the stack grows tall, the Root must perform an additional `segment_query` upwards (or check the top child's volume) to prevent clipping into ceilings.

### 4.2 Dismounting
*   **Voluntary Dismount:**
    *   Check standard offsets (Left, Right, Back).
    *   Use `point_query` or `shape_query` to verify the target spot is free.
    *   Move to the first free spot.
*   **Forced Dismount (e.g., A dies):**
    *   **Deterministic Concentric Search:** If standard offsets are blocked, iterate outward using a strictly defined, discrete pattern (e.g., a "Square Spiral" or "Concentric Diamond" of grid points).
        *   *Implementation:* Use a pre-calculated list of integer offsets `[(1,0), (0,1), (-1,0), (0,-1), (1,1)...]` scaled by the grid size.
        *   **Search Limit:** A tunable `MAX_SEARCH_STEPS` (e.g., 50 iterations) must be enforced. If this limit is exceeded without finding a valid spot, the logic falls back to the failure state.
        *   **Verify:** Check each point using `point_query` or `shape_query`.
    *   **Eject:** Teleport the child to the first valid safe spot found.
    *   *Fallback:* If the search limit is reached (e.g. map is completely full/buried), the entity gets crushed.

## 5. Implementation Roadmap

1.  **Engine Config:** Set Pymunk Space to no gravity (or handle gravity manually in KinematicSystem).
2.  **`KinematicSystem`:**
    *   Implement `move_and_slide` using `space.segment_query`.
    *   Ensure `radius` matches the character's physical collider.
3.  **`HierarchySystem`:**
    *   Implement recursive transform updates.
4.  **Dismount Logic:**
    *   Implement "Find Nearest Safe Spot" algorithm using a deterministic offset table.
    *   Expose `MAX_SEARCH_STEPS` as a configuration constant.

## 6. Why This Wins
*   **True Determinism:** Fixed timestep + explicit resolution rules + discrete search patterns.
*   **Tunneling Solved:** Capsule Cast catches all intermediate obstacles.
*   **High Performance:** Relies on native Pymunk queries rather than Python loops.
*   **Player Friendly:** Robust dismount logic prevents unfair deaths.
