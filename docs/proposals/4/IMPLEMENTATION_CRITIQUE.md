# Critique of Proposal 4: Detailed Implementation Plan

## Strengths

1.  **Clear Core Mechanic:** The "Sweep-and-Slide" approach is a proven method for 2D character controllers, providing precise control and eliminating physics-based jitter.
2.  **Addressing Edge Cases:** The plan explicitly anticipates common pitfalls like "tunneling" (solved by capsule casting) and "snagging on internal edges" (solved by skin width/filters).
3.  **Hierarchy Management:** The recursive update strategy and "Totem Pole" concept for compound colliders show a good understanding of the complexities of attached entities.
4.  **Robust Dismounting:** The "Ghost Mode" / "Pending Dismount" state is an excellent solution to the problem of forced dismounts in crowded areas, prioritizing player fairness over immediate spatial correctness.
5.  **Visibility Optimization:** The pipeline (Distance -> Angle -> Raycast) is a standard and effective optimization pattern.

## Weaknesses and Areas for Improvement

1.  **Pymunk Integration Nuances:**
    *   **"Kinematic" vs "Static" for Walls:** The plan mentions `StaticBody` for walls but later discusses "Runtime Updates". Moving a `StaticBody` is expensive in Chipmunk/Pymunk as it triggers a full spatial hash re-index. If walls move (e.g., doors), they should ideally be `KinematicBody` or a specialized type, or the re-indexing cost must be acknowledged.
    *   **Segment Query vs Shape Query for Sweeps:** `segment_query` is a raycast (or thin capsule). It does *not* represent the full volume of a moving shape (e.g., a box or a wide polygon). If the character is a box, a capsule cast might miss corners. A `shape_query` (sweeping the actual shape) is theoretically more accurate but much more expensive/complex to implement manually if Pymunk doesn't support "Sweep Test" natively (Chipmunk has `cpSpaceShapeQuery` which checks overlap, but "Sweep" usually implies moving a shape along a vector). The proposal conflates "Capsule Cast" (which `segment_query` with radius effectively is) with a generic "Sweep". This is fine for circular characters but could be misleading for non-circular ones.
    *   **Filter Complexity:** Managing collision filters (Groups, Categories, Masks) can get messy. The plan mentions excluding "sensors and the entity's own shapes" but doesn't detail a robust bitmask strategy to handle:
        *   Friendly fire (projectiles).
        *   Vision blocking (opaque vs transparent obstacles).
        *   Movement blocking (low vs high obstacles).

2.  **"Totem Pole" Compound Collider Implementation:**
    *   **Dynamic Shape Updates:** The plan suggests updating the Root's Pymunk shape when the stack changes. Recreating/Modifying shapes on a body at runtime can be tricky and might have performance implications or require re-adding the shape to the space.
    *   **Center of Mass/Pivot:** If the stack is asymmetrical, simply expanding the radius might create a collider that is too large, preventing the unit from fitting through valid gaps. An AABB approach or a composite body (multiple shapes attached to the root) might be better than a single expanded radius.

3.  **Dismount Search Logic:**
    *   **Infinite Ghost Mode:** While "Ghost Mode" is good, leaving a unit in that state "indefinitely" (until map exit) creates a design problem: "Where is my unit? Why can't I use it?". There should be a UI indicator or a forced resolution mechanism (e.g., after X seconds, it teleports to a designated safe zone or the nearest base).

4.  **Input Handling:**
    *   The plan mentions `Input -> Desired Displacement` but glosses over *how* input is processed. Is it immediate? Is there acceleration/deceleration? "Kinematic" often implies instant velocity changes, which can feel stiff. Adding a layer of "Virtual Physics" (calculating velocity with accel/friction *then* moving kinematically) often yields better game feel.

5.  **Interpolation Details:**
    *   Linear interpolation is standard, but for a hierarchy, interpolating the Root and then calculating children position vs. interpolating every child individually can yield different visual results (especially with rotation). The plan implies interpolating the Root's position, but needs to ensure the child transforms are derived from the *interpolated* root position for rendering, not the *physics* root position.

## Revisions to Proposal

Based on this critique, the following revisions will be made to the proposal:

1.  **Clarify Wall Types:** Distinguish between `StaticBody` (immutable geometry) and `KinematicBody` (doors/moving platforms) to avoid performance pitfalls.
2.  **Refine Sweep Logic:** Explicitly state that characters are approximated as Circles/Capsules for the sake of movement physics (`segment_query` with radius). This simplifies the "Sweep" to a "Capsule Cast", which is robust and performant.
3.  **Compound Collider Strategy:** Instead of constantly resizing a single shape, we will use **Composite Shapes**. The Root body will have its own shape, and attached children will add their *sensor* shapes to the Root body (if they need to detect hits) or we simply rely on the Root's shape being "good enough" for movement, while the children keep their hitboxes for damage. Actually, the critique suggests the Root's *movement* collider needs to expand. We will refine this to: "The Root maintains a `MovementCollider` which is the bounding circle of the stack. Children add `Hitbox` shapes (Sensors) to the Root body for damage detection."
4.  **Ghost Mode UI:** Add a requirement for a visual indicator (e.g., "Unit Pending Arrival") and a fallback "Emergency Teleport" to the nearest friendly base if a spot isn't found after a significant duration.
5.  **Input "Virtual Physics":** Add a step to `KinematicMovementSystem` to apply Acceleration/Friction to the input vector *before* the sweep-and-slide, ensuring smooth movement.
6.  **Rendering Interpolation:** Clarify that the `RenderSystem` uses the interpolated Root transform to compute child render transforms, ensuring the entire stack moves smoothly together.
