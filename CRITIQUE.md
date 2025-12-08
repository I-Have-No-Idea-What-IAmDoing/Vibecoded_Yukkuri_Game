# Critique: Proposal 4 - Deterministic Kinematic Hierarchy

This document provides a systematic critique of the current implementation of **Proposal 4** (Deterministic Kinematic Hierarchy), evaluating its adherence to the core principles and the quality of any deviations.

## 1. Core Principle: The Geometry Database

*   **Requirement:** Physics engine should be used primarily for spatial hashing and collision queries, not simulation. All moving entities must be `KinematicBody`.
*   **Implementation:** **Verified.**
    *   `KinematicMovementSystem` explicitly checks `if phys.body.body_type != pymunk.Body.KINEMATIC: continue`.
    *   Movement is controlled manually via `move_and_slide`.
    *   The `PhysicsSystem` still steps the simulation (`space.step`), which is necessary for updating the spatial hash and handling `PhysicsFixedUpdateEvent`, but kinematic bodies are immune to forces.

## 2. Core Mechanic: The Sweep-and-Slide

*   **Requirement:** Fixed Timestep, Input -> Acceleration -> Velocity, Sweep (Capsule Cast), Slide Resolution, Interpolation.
*   **Implementation:** **Verified with Superior Deviations.**
    *   **Fixed Timestep:** Correctly implemented in `PhysicsSystem` using an accumulator loop. `KinematicMovementSystem` subscribes to `PhysicsFixedUpdateEvent` to ensure logic runs exactly once per tick.
    *   **Integration:** Correctly implements `Input -> Acceleration -> Velocity` with friction.
    *   **Sweep:** Correctly uses `space.segment_query` to sweep the volume. It iterates over all shapes in the body (supporting composite shapes), effectively performing a multi-capsule cast.
    *   **Slide Resolution:** Correctly implements vector projection (`remainder - normal * dot`). Handles multiple iterations (corners).
    *   **Deviation (Superior): Pre-step Depenetration.** The implementation adds a `resolve_penetration` step before movement.
        *   *Justification:* Pure sweep assumes you never start inside a wall. In reality (spawning, map editing, growing shapes), overlaps happen. The depenetration step robustly pushes entities out of walls using `shape_query` and contact normals, preventing the "stuck" state that pure sweep can suffer from.

## 3. The Hierarchy: Rigid Locking

*   **Requirement:** `Mount` component, Recursive Update (`Child.Pos = Parent.Pos + Offset`), Children as Sensors.
*   **Implementation:** **Verified.**
    *   `HierarchySystem` performs a recursive stack-based update of positions.
    *   Children shapes are correctly converted to sensors (`child_phys.shape.sensor = True`) to prevent them from physically colliding during the physics step (collision is handled by the Root's sweep).
    *   Dirty flags are used to optimize structure updates.

## 4. Handling Stacks: "The Totem Pole"

*   **Requirement:** Root assumes responsibility. Root maintains a "Simple Bounding Circle" or Capsule.
*   **Implementation:** **Deviation (Superior).**
    *   *Proposal:* "The Root maintains a simple Bounding Circle...".
    *   *Implementation:* The implementation constructs a **Composite Collider** by attaching "Proxy Shapes" (identical to children's shapes) to the Root Body.
    *   *Justification:* A simple bounding circle is often too loose (gaps) or too tight (clipping) for complex stacks. The composite approach allows for exact collision bounds. Since `move_and_slide` iterates over *all* shapes in the body, it performs a rigorous sweep of the entire stack's shape. This is more accurate and robust than a single approximated circle, at a slight performance cost (which is negligible for typical stack sizes).

## 5. Dismounting

*   **Requirement:** Concentric Search, Ghost Mode (Pending Dismount), Emergency Teleport.
*   **Implementation:** **Verified.**
    *   `PendingDismount` component handles the state.
    *   `find_free_spot` implements a spiral search using `space.point_query` with a radius (Volume Check), ensuring the spot is actually large enough for the entity.
    *   Emergency teleport to a fallback position (currently `(0,0)`, potentially needs a `SpawnPoint` service in the future) triggers after a timeout.

## 6. Visibility & Line of Sight

*   **Requirement:** Range Check -> Angle Check -> Raycast. "True Visibility".
*   **Implementation:** **Verified.**
    *   **Broadphase:** Uses `space.point_query` (fast spatial hash lookup) to find entities within range.
    *   **Angle Check:** Dot product check against FOV.
    *   **Raycast:** `space.segment_query` ensures line-of-sight is not blocked by opaque walls. Correctly filters sensors and self.
    *   **Optimization:** Implements time-slicing (`batch_size`) to distribute load across frames.

## 7. Rendering & Interpolation

*   **Requirement:** Interpolate between `prev_pos` and `curr_pos`.
*   **Implementation:** **Verified.**
    *   `PhysicsSystem` and `KinematicMovementSystem` correctly update `prev_x`/`prev_y` before modification.
    *   `RenderSystem` uses `alpha` from the game loop to interpolate position: `interp_x = prev_x + (curr_x - prev_x) * alpha`. This ensures buttery smooth rendering even if the physics tick rate (60Hz) doesn't match the monitor refresh rate (144Hz+).

## Conclusion

The implementation is **excellent** and strictly follows the "Geometry Database" philosophy. The deviations found (Depenetration, Composite Collider for Stacks) are technically superior solutions that solve edge cases inherent in the original proposal without violating its core tenets.

**Verdict:** The current implementation is superior to the original proposal. No changes are required.
