# Critique of Proposal 4 Implementation Plan

This document critiques the detailed implementation plan (`IMPLEMENTATION_PLAN.md`) for Proposal 4.

## 1. Kinematic Controller Robustness

### 1.1 "Stop at Corner" Logic
*   **Issue:** The plan states: *"Acute Corner Check: If the new slide direction immediately hits another wall (creating a pinch point), stop movement"*.
*   **Critique:** Immediately stopping is too conservative and results in sticky player movement. If the player is pushing into a corner, they should ideally slide towards the vertex or stop *at* the vertex, but if they are pushing *along* one wall and hit a second wall at an angle, the expected behavior is often to slide along the second wall if the angle allows.
*   **Risk:** Players getting "stuck" on geometry that feels traversable.

### 1.2 "Internal Edge" Threshold
*   **Issue:** The plan uses a threshold `dot(normal, move_direction) > -0.01` to ignore internal edges.
*   **Critique:** Hardcoded thresholds are fragile.
*   **Recommendation:** Use Pymunk's `ShapeFilter` or `group` property to explicitly link wall segments that belong to the same structure, or use a "radius" in the query that is slightly smaller than the collision shape to avoid catching on seams (the "skin width" concept).

## 2. Hierarchy & Compound Collider Issues

### 2.1 Dynamic Shape Updates
*   **Issue:** "Update the Root's shape... to match this AABB."
*   **Critique:** Rebuilding or modifying Pymunk shapes at runtime (especially every frame during animations or rotation) can be expensive as it triggers spatial hash re-indexing.
*   **Recommendation:** Use a "Max Bounds" approach where the root collider is large enough for the *expected* max stack, or only update on *structural* changes (mount/dismount), not every frame.

### 2.2 Rotation Handling ("Prevent Rotation")
*   **Issue:** "If blocked, prevent rotation... Do not allow the stack to rotate inside a wall."
*   **Critique:** While deterministic and safe, this feels unresponsive. If a player turns their mouse/stick, and the character refuses to rotate because a mounted gun would hit a wall, it feels like the input is broken.
*   **Recommendation:** This is a trade-off. A better (but harder) approach is to push the character away from the wall to accommodate the rotation. If "Prevent Rotation" is chosen, there must be clear audio-visual feedback (e.g., a "clunk" sound and spark) so the user knows *why* they can't turn.

## 3. Pending Dismount Logic

### 3.1 "Every Frame" Retry
*   **Issue:** "Every frame... it retries the dismount search."
*   **Critique:** If there are 50 ghosts stuck in a wall, this is 50 expensive searches per frame.
*   **Recommendation:** Throttle to every 10-20 frames, or use an event-based trigger (e.g., "nearby space became free").

### 3.2 Destruction Timeout
*   **Issue:** "Only destroy after... 5-10 seconds".
*   **Critique:** Why destroy at all? If a unit is "stuck" in a pending dismount, it's effectively out of play. Destroying it punishes the player for a pathfinding/collision edge case.
*   **Recommendation:** Keep them in "Ghost Mode" indefinitely until retrieved, or make them "Emergency Eject" to the nearest valid point on the map (even if far away), or return to a "Reserve" pool.

## 4. Visibility Ambiguities

### 4.1 "Characters Block Sight"
*   **Issue:** The plan says: *"Ignore sensors and other characters (unless characters block sight)."*
*   **Critique:** This is contradictory. If characters block sight, they cannot be ignored in the query.
*   **Clarification:** The query must include `COLLISION_TYPE_CHARACTER` in the filter. The logic must then distinguish:
    *   Hit Wall -> Not Visible.
    *   Hit Enemy -> Blocked (Not Visible, unless the Enemy IS the target).
    *   Hit Target -> Visible.
    *   This requires a more nuanced filter or post-processing the hit result.

## 5. Input & Rendering Latency

### 5.1 Interpolation
*   **Issue:** The plan specifies "Fixed Timestep" and "Manually set body.position".
*   **Critique:** Without interpolation between the previous physics state and the current state, the rendering will jitter if the frame rate doesn't perfectly match the physics rate (which it never does).
*   **Recommendation:** The implementation must include `render_position = lerp(prev_pos, curr_pos, alpha)` where `alpha` is the accumulator fraction.

## 6. Testing Strategy

### 6.1 Mocks vs. Real Physics
*   **Issue:** "Unit Tests... with mock geometry".
*   **Critique:** Mocking Pymunk is dangerous because the "Database" behavior is exactly what we need to verify.
*   **Recommendation:** Use "Headless Pymunk" for unit tests. Initialize a real `pymunk.Space`, add real bodies, and step the simulation. It's fast and much more reliable than mocking.
