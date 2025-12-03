# Critique of Proposal 4: Deterministic Kinematic Hierarchy (Round 2)

## 1. Feasibility of "Shape Cast" in Pymunk
The proposal relies on "Shape Cast (Sweep)" to ensure zero tunneling. However, `pymunk` (and Chipmunk Physics) does not natively support continuous collision detection (swept shapes) for arbitrary polygons/boxes. It only supports:
1.  **Static Overlap:** `shape_query` (Is shape X overlapping anything *right now*?)
2.  **Raycast:** `segment_query` (Does this line hit anything?)

**Critique:** "Performing a shape sweep" is not a primitive operation. Implementing it via iterative stepping (moving the shape slightly, checking, repeating) is expensive (O(N) queries per entity per frame) and imprecise (tunneling still possible between steps).

**Recommendation:**
*   Acknowledge the limitation.
*   Propose a **Hybrid Approach**: Use a `segment_query` (Raycast) from the center to detect high-speed collisions preventing tunneling, combined with `shape_query` at the destination to handle volume.
*   Or, explicitly define the "Sweep" as an iterative "Linear Cast" with a fixed step size (e.g., radius of the shape).

## 2. The "Middle Rider" Clipping Issue
The proposal handles the Root (collision) and the Top Rider ("Head Check"). It ignores any riders in between.
*   **Critique:** If a middle rider is wider than the Root, they will clip through walls. If they are taller than the gap allows (but shorter than the top rider?), they might intersect geometry that the top rider misses (e.g. an overhang at mid-height).
*   **Recommendation:**
    *   Instead of just a "Head Check", the system should perform a **Stack Check**.
    *   Iterate through *all* attached children. If *any* child's shape at the target position overlaps an obstacle, the movement is blocked.
    *   This effectively treats the stack as a **Composite Collider** without the overhead of physically welding bodies.

## 3. Ghost Collisions (Tilemap Seams)
The "Slide" logic works well on single continuous planes. However, on tilemaps, a floor is often made of many adjacent box colliders.
*   **Critique:** A Box collider sliding along a tiled floor will often "catch" on the internal vertices between tiles due to floating-point errors, causing the entity to stop or "trip" on a flat surface.
*   **Recommendation:**
    *   Suggest using **Capsule** or **Chamfered Box** (octagon) shapes for the Root entity. Rounded bottoms slide over internal seams much smoother than flat-bottomed boxes.

## 4. Interaction with Dynamic Bodies
The proposal treats the world as a "Geometry Database" (Walls/Floors).
*   **Critique:** It is undefined what happens when a kinematic Root hits a Dynamic Body (e.g., a crate). The current logic ("Detect Hit -> Stop") treats a 1kg crate as an immovable wall.
*   **Recommendation:**
    *   Clarify that for this iteration, **Dynamic Bodies are Obstacles**. Interaction/Pushing is out of scope or requires a specific "Push" state that temporarily overrides the "Stop" behavior.
