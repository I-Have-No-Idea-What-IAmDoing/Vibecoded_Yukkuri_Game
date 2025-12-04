# Implementation Plan - Proposal 4: Deterministic Kinematic Hierarchy

This document outlines the detailed implementation plan for Proposal 4, incorporating feedback from the critique. The goal is to build a deterministic, robust character controller and hierarchy system using Pymunk as a geometry database.

## Phase 1: Core Kinematic Controller (`KinematicMovementSystem`)

The foundation of the system is the "Sweep-and-Slide" movement logic. This must be implemented with strict adherence to determinism and robustness against geometry edge cases.

### 1.1 Configuration
*   **Pymunk Space:** Configure the Pymunk Space to have **zero gravity**.
*   **Body Types:**
    *   **Characters:** `pymunk.Body.KINEMATIC`.
    *   **Walls:** `pymunk.Body.STATIC` (for immutable geometry).
    *   **Doors/Moving Platforms:** `pymunk.Body.KINEMATIC` (allows movement without re-indexing).

### 1.2 The `move_and_slide` Algorithm
Implement a function `move_and_slide(body, input_vector, dt, current_velocity, properties)`:
1.  **Virtual Physics:**
    *   Apply `acceleration` to `current_velocity` towards `input_vector`.
    *   Apply `friction` to `current_velocity` (damping).
    *   `move_delta = current_velocity * dt`.
2.  **Iterative Sweep:** Perform up to 3 iterations of the following:
    *   **Cast:** Use `space.segment_query(start, end, radius, filter)` to detect collisions.
        *   `radius`: Matches the character's collider radius (Capsule Cast).
        *   `filter`: Bitmask to exclude sensors and self.
    *   **No Hit:** If no collision, move the full remaining distance and break.
    *   **Hit:**
        *   Move the entity to `hit_point + normal * epsilon` (safe distance).
        *   **Internal Edge Handling:** Use `ShapeFilter` or a small "skin width" reduction in the query radius to avoid catching on seams.
        *   **Slide:** Calculate the remainder vector. Project it onto the wall tangent: `remainder = remainder - normal * dot(remainder, normal)`.
        *   **Corner Handling:** If the new slide direction hits another wall:
            *   Attempt to slide along the *second* wall's tangent.
            *   If the projected movement along the second wall opposes the original intent (dot product < 0) or is blocked, stop movement.
    *   **Update Position:** Manually set `body.position`.

### 1.3 Validation
*   **Test Case:** "The Hallway" - Move parallel to a wall composed of multiple segments. Ensure no snagging on vertices.
*   **Test Case:** "The Corner" - Move into an acute corner. Ensure the character stops cleanly or slides into the apex without jittering.

## Phase 2: Hierarchy & Mounting (`HierarchySystem`)

This system manages attached entities (turrets, passengers) and ensures they move with their parent.

### 2.1 `Mount` Component
Create the `Mount` component as defined in the proposal:
*   `parent_id`: Entity ID of the parent (or -1).
*   `children_ids`: List of child Entity IDs.
*   `mount_point_offset`: `Vector2` relative to parent.
*   `layer_order`: Rendering order.

### 2.2 Recursive Transform Updates
Implement a system that runs **after** `KinematicMovementSystem`:
1.  Identify Root entities (entities with `Mount` component but no `parent_id`).
2.  Traverse the hierarchy tree.
3.  Update Child Transform: `Child.Pos = Parent.Pos + rotate_vector(Child.Offset, Parent.Rotation)`.
4.  **Dirty Flags:** Optimize by only updating sub-trees where the root or a node has moved/rotated.

### 2.3 Compound Shapes (Movement vs Hitbox)
To handle "Totem Pole" stacks correctly:
1.  **Movement Collider (Root):** The Root entity maintains a `MovementCollider` (Circle/Capsule) large enough to encompass the stack. This is the *only* shape used for the `move_and_slide` sweep.
2.  **Hitboxes (Children):**
    *   Children attached to the root have `Hitbox` shapes.
    *   These are set as **Sensors** in Pymunk.
    *   They move with the child (logically) or are attached to the Root body (physically) with offsets.
3.  **Rotation Constraints:**
    *   **Predict:** Before applying rotation, check `shape_query` at the target rotation.
    *   **Prevent:** If blocked, do not rotate. Trigger a "Blocked" feedback event (sound/spark).

## Phase 3: Dismount Logic

Robust logic for handling entities leaving the hierarchy, either voluntarily or forcibly.

### 3.1 "Pending Dismount" State (Ghost Mode)
To address the critique about unfair destruction:
*   Create a `PendingDismount` component.
*   **Behavior:**
    *   The entity is detached from the parent logically but follows it visually (or stays at last valid point).
    *   It is non-interactive and invisible (or semitransparent with an icon).
    *   **Throttle:** Every 10-20 frames, it retries the dismount search.
    *   **Success:** If a spot opens up, it materializes there and removes the component.
    *   **Emergency Teleport:** If `time_in_pending > TIMEOUT`, teleport to the nearest designated "Safe Zone" (e.g., spawn point) to prevent indefinite limbo.

### 3.2 Deterministic Concentric Search
Implement the search algorithm for finding a safe spot:
1.  **Standard Offsets:** Check Left, Right, Back, Front relative to parent.
2.  **Spiral Search:** If standard fails, iterate through a pre-calculated list of grid offsets.
3.  **Validation:** For each candidate point, perform a `point_query` and/or `shape_query` (checking the entity's footprint).
4.  **Result:** Move to the first valid point found.

## Phase 4: Visibility System (`VisibilitySystem`)

A performant "True Visibility" system using the geometry database.

### 4.1 Filter Strategy
Define a robust Bitmask strategy:
*   `CATEGORY_WALL`
*   `CATEGORY_UNIT`
*   `CATEGORY_SENSOR`
*   `MASK_VISION_BLOCKER` = `CATEGORY_WALL` (and optionally `CATEGORY_UNIT`)

### 4.2 Optimization Pipeline (Broadphase First)
Implement `is_visible(observer, target)` with strict ordering:
1.  **Distance Check:** `distance_sq(obs, target) <= range_sq`. (Fastest).
2.  **Angle Check:** If `FOV < 360`, check if `dot(obs_fwd, target_dir) > cos(FOV/2)`.
3.  **Raycast:** Only if above pass, perform `space.segment_query(obs_pos, target_pos)`.
    *   **Filter:** `MASK_VISION_BLOCKER`.
    *   **Logic:** The ray will hit the closest object.
        *   If Hit Object == Target: **Visible**.
        *   If Hit Object == Wall: **Blocked**.

### 4.3 Throttling
*   **Time-Slicing:** Update 10-20% of the entities per frame in a round-robin fashion.
*   **Event-Based:** Trigger updates on movement or door state changes.

## Phase 5: Input & Rendering

### 5.1 Interpolation
*   **Fixed Timestep:** Physics runs at fixed `dt` (e.g., 60Hz).
*   **Variable Render:** Rendering runs at monitor refresh rate.
*   **Interpolation Logic:**
    1.  Compute `alpha` (accumulator / fixed_dt).
    2.  Interpolate **Root** Position/Rotation: `root_render_pos = lerp(root_prev, root_curr, alpha)`.
    3.  **Derived Children:** Calculate Child render transforms based on the *interpolated* Root transform: `child_render_pos = root_render_pos + rotate(child.offset, root_render_rot)`.
    *   *Do not interpolate children individually, as this causes detachment artifacts.*

## Phase 6: Testing & Verification Strategy

1.  **Headless Pymunk Tests:**
    *   Create a `pymunk.Space` without graphics.
    *   Add walls and a kinematic body.
    *   Step the simulation and assert positions to verify `move_and_slide`, corner handling, and internal edge skipping.
2.  **Visual Debugging:**
    *   Draw "Sweep" capsules, collision normals, and dismount search points.
3.  **Stress Tests:**
    *   Spawn 100+ units.
    *   Verify framerate stability with `move_and_slide` and Visibility systems active.
