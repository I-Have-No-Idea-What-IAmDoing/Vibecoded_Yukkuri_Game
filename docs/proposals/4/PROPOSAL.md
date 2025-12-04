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
    *   **Radius:** Use the Root entity's collision radius. This effectively performs a "Circle Sweep" or "Capsule Cast", ensuring **Zero Tunneling** for linear movement.
    *   **Filter:** Exclude Sensors and the entity's own shapes.
3.  **Resolve Collision:**
    *   If the query returns a hit at fraction `alpha` (0 to 1):
        *   The safe movement is `move_delta * (alpha - epsilon)`.
        *   **Slide:** Calculate the remainder vector (`move_delta * (1-alpha)`). Project this vector onto the wall's surface tangent (using the `normal` returned by the query).
        *   **Corner Handling:** If the slide vector immediately hits another wall (acute corner), stop movement to prevent jitter.
        *   **Internal Edges:** Ignore collisions with normals opposing the movement direction significantly less than 90 degrees to prevent catching on flat wall seams.
        *   **Repeat:** Perform a second sweep with the projected "slide" vector. (Max 3 iterations).
    *   If no hit: Move the full `move_delta`.
4.  **Commit:** Manually set `body.position`. The body **must** be a `pymunk.Body.KINEMATIC` to ensure it doesn't fight the physics solver.

### 2.2 Why `segment_query`?
*   **Performance:** It is a native C function in Chipmunk/Pymunk.
*   **Correctness:** It checks the continuous volume between start and end, preventing "bullet through paper" tunneling.
*   **Simplicity:** It returns the exact surface normal and impact point, making "Sliding" math trivial.

### 2.3 Static Geometry (Walls & Obstacles)
Walls and other static obstacles are the backbone of the "Geometry Database".
*   **Definition:** They are `StaticBody` instances in Pymunk with attached shapes (Segments or Polygons).
*   **Collision Type:** They are assigned a specific collision type (e.g., `COLLISION_TYPE_OBSTACLE`) to distinguish them from characters, sensors, or projectiles.
*   **Function:** They serve as immutable barriers for the Sweep-and-Slide mechanic.
*   **Creation:** Defined at map load time (tilemap) OR **instantiated at runtime** (player-placed fortifications).
*   **Runtime Updates:** When a player places a wall, a new `StaticBody` and `Shape` are added to the Pymunk Space. The Spatial Hash automatically updates, ensuring that subsequent Raycasts and Sweeps immediately respect the new barrier.
*   **Placement Validation:** To place a wall, the system first performs a `shape_query` (checking the wall's intended footprint). Placement is allowed only if the query returns no collisions with characters or existing critical infrastructure.
*   **Optimization:** Pymunk automatically indexes static bodies in a spatial hash, ensuring that queries against thousands of wall segments remain efficient.

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
*   **Movement Collider:** The Root's effective collider **must expand** to encompass the bounding box of the entire stack.
    *   *Implementation:* If a child is wider than the root, the Root's sweep radius increases.
    *   *Rotational Sweeping:* If the stack rotates, we must perform a `shape_query` sweep or simply restrict rotation if it would cause a collision. Pure linear `segment_query` is insufficient for rotating wide stacks.
*   **Ceiling Checks:** The Root **must** perform an upward check (relative to its own top) equal to the total height of the stack. This prevents the "head" of the stack from clipping through doorframes or low ceilings.

### 4.2 Dismounting
*   **Voluntary Dismount:**
    *   Check standard offsets (Left, Right, Back).
    *   Use `point_query` or `shape_query` to verify the target spot is free.
    *   Move to the first free spot.
*   **Forced Dismount (e.g., A dies):**
    *   **Deterministic Concentric Search:** If standard offsets are blocked, iterate outward using a strictly defined, discrete pattern.
        *   *Implementation:* Use a pre-calculated list of integer offsets `[(1,0), (0,1), (-1,0), (0,-1), (1,1)...]` scaled by the grid size.
        *   **Search Limit:** A tunable `MAX_SEARCH_STEPS` (e.g., 50 iterations).
        *   **Verify:** Check each point using `point_query` or `shape_query`.
    *   **Eject:** Teleport the child to the first valid safe spot found.
    *   **Graceful Failure:** If the search limit is reached:
        *   **Do NOT destroy the entity.**
        *   Enter a **"Pending Dismount"** state. The entity remains attached (or becomes a "ghost" at the last known valid location) and retries the search on the next frame (possibly with a wider radius or waiting for other units to move).
        *   Only destroy if the situation is unresolvable for T seconds.

## 5. Visibility & Line of Sight

To support tactical gameplay, we implement a "True Visibility" system that integrates seamlessly with our Geometry Database.

### 5.1 The `Vision` Component
Entities capable of seeing (Characters, Cameras, Turrets) possess a `Vision` component:
*   **Range:** The maximum distance the entity can see.
*   **Field of View (FOV):** An angle limit for directional sight (e.g., 90 degrees).

### 5.2 Raycasting Strategy
Visibility is determined by casting rays against the physical environment.
*   **Query:** `pymunk.Space.segment_query`.
*   **Filtering:** Stop on `COLLISION_TYPE_OBSTACLE`. Ignore Sensors/Characters.

### 5.3 Optimization: "Broadphase First"
*   **Distance Check:** `dist(observer, target) <= vision_range`. **Strictly check this first.**
*   **Angle Check (Sector):** If `FOV < 360`, check if the target vector lies within the observer's forward cone. Dot product check is cheap. **Check this second.**
*   **Raycast Last:** Only perform the expensive `segment_query` if Distance and Angle checks pass.
*   **Throttling:** Run visibility updates at a lower frequency (e.g., 10Hz) or time-slice them (update 10% of units per frame).

## 6. Implementation Roadmap

1.  **Engine Config:** Set Pymunk Space to no gravity. Use `KinematicBody` for all movers.
2.  **`KinematicSystem`:**
    *   Implement `move_and_slide` using `space.segment_query` with multi-iteration slide.
    *   Implement "Internal Edge" filtering.
3.  **`HierarchySystem`:**
    *   Implement recursive transform updates.
    *   Add "Compound Bounds" calculation for the Root based on children.
4.  **Dismount Logic:**
    *   Implement "Concentric Search".
    *   Implement "Pending Dismount" queue.
5.  **`VisibilitySystem`:**
    *   Implement `is_visible` with Distance -> Angle -> Raycast pipeline.

## 7. Why This Wins
*   **True Determinism:** Fixed timestep + explicit resolution rules + discrete search patterns.
*   **Tunneling Solved:** Capsule Cast catches all intermediate obstacles.
*   **Robust:** Handles corner cases and stuck scenarios gracefully.
*   **Tactical Depth:** True wall-blocked visibility.
*   **Player Friendly:** "Pending Dismount" prevents unfair deaths.
