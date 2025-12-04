# Proposal 4: Deterministic Kinematic Hierarchy (The "Controller" Pattern)

We treat the Physics Engine effectively as a "Geometry Database". We query it to ask "Can I move here?", but we never let it move objects for us.

## 1. Core Principle: The Geometry Database
*   **Physics as a Query Engine:** We use Pymunk not for simulation, but for its optimized spatial hashing and collision detection algorithms.
*   **Kinematic Control:** All moving entities are `KinematicBody`. They do not respond to forces or gravity. Their position is set explicitly each frame.

## 2. Core Mechanic: The Sweep-and-Slide

Instead of `Force -> Velocity -> Position` (Physics), we use `Input -> Acceleration/Friction -> Desired Displacement -> Allowed Displacement -> Position`.

**Crucial:** This logic must run on a **Fixed Timestep** (e.g., 60Hz) to ensure `dt` is constant, guaranteeing 100% determinism.

### 2.1 The Movement Logic
For every moving entity (Root):
1.  **Virtual Physics:** Apply acceleration and friction to the input vector to determine the current `velocity`. This ensures movement feels weighty, not twitchy.
2.  **Calculate Desired Vector:** `move_delta = velocity * fixed_dt`.
3.  **The Sweep (Capsule Cast):**
    *   **Approximation:** We approximate characters as Circles or Capsules for movement physics. This allows us to use `pymunk.Space.segment_query` with a radius.
    *   **Query:** Detect the **First Impact** along the path.
    *   **Radius:** Use the Root entity's collision radius. This ensures **Zero Tunneling**.
    *   **Filter:** Exclude Sensors and the entity's own shapes.
4.  **Resolve Collision:**
    *   If the query returns a hit at fraction `alpha` (0 to 1):
        *   The safe movement is `move_delta * (alpha - epsilon)`.
        *   **Slide:** Calculate the remainder vector (`move_delta * (1-alpha)`). Project this vector onto the wall's surface tangent (using the `normal` returned by the query).
        *   **Corner Handling:** If the slide vector hits another wall, attempt to slide along the *second* wall's tangent. If that is also blocked or opposes the original intent, stop.
        *   **Internal Edges:** Use a "skin width" or Pymunk's group filtering to ignore internal seams of composite walls.
        *   **Repeat:** Perform a second sweep with the projected "slide" vector. (Max 3 iterations).
    *   If no hit: Move the full `move_delta`.
5.  **Commit:** Manually set `body.position`. The body **must** be a `pymunk.Body.KINEMATIC` to ensure it doesn't fight the physics solver.
6.  **Interpolation:** For rendering, linearly interpolate between the `previous_position` and `current_position` based on the fraction of the fixed timestep accumulator.

### 2.2 Why `segment_query`?
*   **Performance:** It is a native C function in Chipmunk/Pymunk.
*   **Correctness:** It checks the continuous volume between start and end, preventing "bullet through paper" tunneling.
*   **Simplicity:** It returns the exact surface normal and impact point, making "Sliding" math trivial.

### 2.3 Static & Dynamic Geometry
*   **Walls (Static):** Use `StaticBody` for immutable geometry. Updating these is expensive (re-hashing).
*   **Doors/Platforms (Dynamic):** Use `KinematicBody`. These can move/rotate without triggering a full spatial hash rebuild.
*   **Placement Validation:** `shape_query` checks for overlaps before placement.

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

1.  **Dirty Flag Optimization:** Process the hierarchy for a Root if transform or structure changed.
2.  **Recursive Update:** `Child.Position = Parent.Position + Parent.Rotation * Child.Offset`
3.  **Collision Handling:**
    *   Mounted children convert their physical shapes to **Sensors**.
    *   They do not physically block movement (handled by the Root's Sweep) but can detect overlaps (e.g. for taking damage).

## 4. Handling Stacks & Interactions

### 4.1 "The Totem Pole" (Compound Collider)
When entities are stacked, the Root entity assumes responsibility for the movement of the whole stack.
*   **Movement Collider:** The Root maintains a simple **Bounding Circle** or **Capsule** that encompasses the stack for movement physics.
    *   *Implementation:* On structure change, recalculate the radius required to cover the new stack.
*   **Hitboxes:** Children attach their shapes as **Sensors** to the Root body (or keep them on their own bodies moving in sync). This allows individual parts of the stack to take damage.
*   **Rotational Sweeping:**
    *   If the stack is non-circular (wide), rotation checks are required.
    *   **Prevent Rotation:** If a rotation would cause a collision, block the rotation and provide feedback (audio/visual).
*   **Ceiling Checks:** The Root **must** perform an upward check equal to the total height of the stack.

### 4.2 Dismounting
*   **Voluntary Dismount:** Check offsets, use `point_query`, move to first free spot.
*   **Forced Dismount (e.g., A dies):**
    *   **Deterministic Concentric Search:** Iterate outward using a pre-calculated offset pattern.
    *   **Search Limit:** A tunable `MAX_SEARCH_STEPS`.
    *   **Graceful Failure (Ghost Mode):** If the search limit is reached:
        *   **Do NOT destroy the entity.**
        *   Enter a **"Pending Dismount"** state (Ghost Mode).
        *   **Visuals:** The entity is rendered transparent or with a "Pending" icon.
        *   **Logic:** It retries the search periodically.
        *   **Fallback:** If not placed after X seconds, perform an **Emergency Teleport** to the nearest friendly base/spawn point.

## 5. Visibility & Line of Sight

To support tactical gameplay, we implement a "True Visibility" system.

### 5.1 The `Vision` Component
*   **Range:** Max distance.
*   **Field of View (FOV):** Angle limit.

### 5.2 Raycasting Strategy
*   **Query:** `pymunk.Space.segment_query`.
*   **Filtering:** Use Collision Categories/Masks to distinguish between:
    *   `Opaque` (Walls - Blocks Vision & Move)
    *   `Transparent` (Glass - Blocks Move, Permits Vision)
    *   `Unit` (Blocks Move, optionally Blocks Vision)
*   **Logic:**
    *   Hit nothing? -> Visible (if within range/FOV).
    *   Hit Target first? -> Visible.
    *   Hit Opaque Obstacle first? -> Blocked.

### 5.3 Optimization: "Broadphase First"
*   **Distance Check:** Strictly first.
*   **Angle Check:** Second.
*   **Raycast Last:** Only if Distance and Angle pass.
*   **Throttling:** Time-slice updates (e.g., 10% of units per frame).

## 6. Implementation Roadmap

1.  **Engine Config:** Pymunk Space (No Gravity), KinematicBody, Collision Filters.
2.  **`KinematicSystem`:** `move_and_slide` with Virtual Physics (Accel/Friction).
3.  **`HierarchySystem`:** Recursive updates, Composite Shape management (Movement vs Hitbox).
4.  **Dismount Logic:** Concentric Search + Ghost Mode + Emergency Teleport.
5.  **`VisibilitySystem`:** Broadphase optimization + correct blocking logic.
6.  **`RenderSystem`:** Interpolation logic (Root Interp -> Child Transform).

## 7. Why This Wins
*   **True Determinism:** Fixed timestep + explicit resolution rules.
*   **Tunneling Solved:** Capsule Cast.
*   **Robust:** Handles corner cases and stuck scenarios gracefully (Ghost Mode).
*   **Tactical Depth:** True visibility (walls and units block sight).
