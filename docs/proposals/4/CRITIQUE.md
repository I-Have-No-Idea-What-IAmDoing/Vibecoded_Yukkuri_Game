# Critique of Proposal 4: Deterministic Kinematic Hierarchy

## 1. Critical Flaw: Tunneling
The proposed collision detection method ("Check at Target Position" followed by Binary Search) is fundamentally flawed because it fails to detect obstacles between the start and end positions.
*   **The Problem:** If an entity moves 10 units in a frame but encounters a thin wall at unit 5. The "Check at Target" (unit 10) will report no collision (assuming the wall is thin). The entity will teleport through the wall.
*   **Binary Search Ineffectiveness:** The Binary Search is only triggered *if* the target check fails. If the target check passes (false negative), the binary search never runs.
*   **Requirement:** A proper "Sweep" (detecting the first collision along a path) is required, not just a static check at the destination.

## 2. Performance & Complexity
*   **Python Overhead:** Implementing a custom Binary Search loop in Python for *every* moving entity *every* frame is a performance bottleneck. Pymunk/Chipmunk are written in C for speed; moving the collision resolution loop into Python negates this benefit.
*   **Redundant Logic:** Pymunk already provides `Space.segment_query` (Raycast), and crucially, `segment_query` accepts a `radius` parameter.
    *   `segment_query` with `radius=r` is mathematically equivalent to sweeping a Circle of radius `r` along a line.
    *   This is a native C operation, instant, and handles tunneling perfectly.

## 3. Shape Limitations
*   The proposal suggests using "Root's shape AND all Children's shapes". If these shapes are arbitrary Polygons (Boxes), `segment_query` (Capsule Cast) is less effective.
*   **Recommendation:** Character Controllers should standardly use Capsules (or Circles) for their movement collision. Attached "Children" (stacks) can add to the vertical height (lengthening the capsule) or radius. Using arbitrary polygons for a Kinematic Character Controller complicates "sliding" math significantly (catching corners).

## 4. Dismount Logic & Determinism
*   **"Fail if blocked":** This can lead to player frustration. If I'm next to a wall, I can't get off?
*   **"CRUSH":** Instant death for a "forced dismount" (e.g., bottom player dies) is harsh.
*   **Improvement:** An "Emergency Eject" mechanism is needed.
*   **Determinism Risk:** A naive "Spiral Search" (calculating positions via `sin`/`cos` and floats) introduces non-determinism across different platforms/architectures.
    *   **Recommendation:** The search algorithm must use a **Discrete Concentric Pattern** (e.g., a pre-defined grid of offsets) to guarantee 100% determinism.
*   **Performance Risk:** An unbounded search (e.g., until a free spot is found) could freeze the game loop if the map is dense or the entity is deeply buried.
    *   **Recommendation:** Implement a strict **Tunable Search Limit** (e.g., max 50 checks). If the limit is reached, revert to the fallback behavior (Crush/Damage).

## 5. Hierarchy Update Order
*   The proposal says `HierarchySystem` runs *after* `KinematicMovementSystem`.
*   If the Root moves, the Children update their position. This is correct for rendering.
*   However, if the "Sweep" depends on Children's shapes, the Children's shapes must be at the *correct relative offset* before the sweep starts. The order seems fine, assuming `Mount` offsets are static or updated before physics.

# Recommendations for Revision

1.  **Adopt `segment_query` (Capsule Sweep):** Replace the "Check + Binary Search" logic with Pymunk's native `segment_query(start, end, radius)`. This solves Tunneling and Performance instantly.
2.  **Standardize on Capsule/Circle Colliders:** For the "Movement" logic, approximate the stack as a Capsule (or collection of Circles). This simplifies the sweep and slide math.
3.  **Refine Dismount:** Implement a **Deterministic Concentric Search** with a **Configurable Limit**. Use rigid grid offsets to prevent crushing where possible, but stop searching after N attempts to preserve performance.
