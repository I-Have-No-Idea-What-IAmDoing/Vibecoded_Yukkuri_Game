# Implementation Plan - Proposal 4: Deterministic Kinematic Hierarchy

This document outlines the detailed implementation plan for Proposal 4, incorporating feedback from the critique. The goal is to build a deterministic, robust character controller and hierarchy system using Pymunk as a geometry database.

## Phase 1: Core Kinematic Controller (`KinematicMovementSystem`)

The foundation of the system is the "Sweep-and-Slide" movement logic. This must be implemented with strict adherence to determinism and robustness against geometry edge cases.

### 1.1 Configuration
*   **Pymunk Space:** Configure the Pymunk Space to have **zero gravity**.
*   **Body Type:** All controlled characters must use `pymunk.Body.KINEMATIC`. This ensures they are not affected by the physics solver's forces but still participate in queries.

### 1.2 The `move_and_slide` Algorithm
Implement a function `move_and_slide(body, velocity, dt)`:
1.  **Calculate Movement:** `move_delta = velocity * dt`.
2.  **Iterative Sweep:** Perform up to 3 iterations of the following:
    *   **Cast:** Use `space.segment_query(start, end, radius, filter)` to detect collisions.
        *   `radius`: Matches the character's collider radius (Capsule Cast).
        *   `filter`: Exclude sensors and the entity's own shapes.
    *   **No Hit:** If no collision, move the full remaining distance and break.
    *   **Hit:**
        *   Move the entity to `hit_point + normal * epsilon` (safe distance).
        *   **Internal Edge Handling:** If `dot(normal, move_direction) > -0.01` (approx 90 degrees), ignore this "wall" as it might be a seam. Continue the sweep or nudge slightly and retry.
        *   **Slide:** Calculate the remainder vector. Project it onto the wall tangent: `remainder = remainder - normal * dot(remainder, normal)`.
        *   **Acute Corner Check:** If the new slide direction immediately hits another wall (creating a pinch point), stop movement to prevent jitter.
    *   **Update Position:** Manually set `body.position`.

### 1.3 Validation
*   **Test Case:** "The Hallway" - Move parallel to a wall composed of multiple segments. Ensure no snagging on vertices.
*   **Test Case:** "The Corner" - Move into an acute corner. Ensure the character stops cleanly without jittering or passing through.

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

### 2.3 Compound Collider & Rotation
To handle "Totem Pole" stacks correctly:
1.  **Dynamic Root Collider:** The Root entity's physical collider must potentially expand to encompass the bounding box of its children.
    *   *Approach:* Calculate the AABB of the entire stack. Update the Root's shape (or add auxiliary shapes) to match this AABB.
2.  **Ceiling Check:** Before moving, the Root must perform a `segment_query` upwards from its top to the maximum height of the stack to prevent head-clipping.
3.  **Rotation Constraints:** If the stack is wide:
    *   Perform a `shape_query` at the target rotation.
    *   If blocked, **prevent rotation** or clamp it to the available angle. Do not allow the stack to rotate inside a wall.

## Phase 3: Dismount Logic

Robust logic for handling entities leaving the hierarchy, either voluntarily or forcibly.

### 3.1 "Pending Dismount" State (Ghost Mode)
To address the critique about unfair destruction:
*   Create a `PendingDismount` component or state.
*   If an entity cannot find a valid spot to dismount, it enters this state.
*   **Behavior:**
    *   The entity remains attached visually (or follows as a ghost).
    *   It is non-interactive.
    *   Every frame (or every N frames), it retries the dismount search.
    *   If a spot opens up, it materializes there and leaves the state.
    *   Only destroy after a significant timeout (e.g., 5-10 seconds) or if the parent is destroyed and no spot is found.

### 3.2 Deterministic Concentric Search
Implement the search algorithm for finding a safe spot:
1.  **Standard Offsets:** Check Left, Right, Back, Front relative to parent.
2.  **Spiral Search:** If standard fails, iterate through a pre-calculated list of grid offsets: `[(1,0), (0,1), (-1,0), (0,-1), (1,1), ...]`.
3.  **Validation:** For each candidate point, perform a `point_query` and/or `shape_query` (checking the entity's footprint).
4.  **Result:** Move to the first valid point found.

## Phase 4: Visibility System (`VisibilitySystem`)

A performant "True Visibility" system using the geometry database.

### 4.1 Optimization Pipeline (Broadphase First)
Implement `is_visible(observer, target)` with strict ordering:
1.  **Distance Check:** `distance_sq(obs, target) <= range_sq`. (Fastest).
2.  **Angle Check:** If `FOV < 360`, check if `dot(obs_fwd, target_dir) > cos(FOV/2)`.
3.  **Raycast:** Only if above pass, perform `space.segment_query(obs_pos, target_pos)`.
    *   **Filter:** Stop on `COLLISION_TYPE_OBSTACLE`. Ignore sensors and other characters (unless characters block sight).

### 4.2 Throttling
*   **Time-Slicing:** Do not update all entities every frame. Update 10-20% of the entities per frame in a round-robin fashion.
*   **Event-Based:** Trigger immediate updates only when an entity moves significantly or a door opens/closes.

## Phase 5: Testing & Verification Strategy

Since this system replaces standard physics, verification is crucial.

1.  **Unit Tests:**
    *   Test `move_and_slide` with mock geometry (walls, corners).
    *   Test hierarchy transform math.
    *   Test visibility calculations (sector checks).
2.  **Visual Debugging:**
    *   Draw the "Sweep" capsules and collision normals.
    *   Draw the "Dismount Search" points (green for valid, red for blocked).
    *   Draw FOV cones and raycasts.
3.  **Stress Tests:**
    *   Spawn 100+ units and check framerate (verify spatial hash and visibility culling).
    *   Stack 10+ entities and move/rotate near walls.
