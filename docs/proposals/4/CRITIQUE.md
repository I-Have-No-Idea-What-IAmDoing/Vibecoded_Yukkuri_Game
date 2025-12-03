# Critique of Proposal 4 (Revised)

## 1. Feasibility of "Shape Sweep" in Pymunk
The proposal relies heavily on a "Shape Cast (Sweep)" to prevent tunneling. However, Pymunk (and the underlying Chipmunk physics engine) does **not** natively support "sweeping" a shape along a vector to find the time-of-impact (TOI).
*   **Discrete Stepping:** Implementing this via `shape_query` at discrete intervals is computationally expensive and does not strictly guarantee "Zero Tunneling" (small obstacles could still be skipped between steps).
*   **Complexity:** Building a custom Continuous Collision Detection (CCD) system on top of Pymunk is non-trivial and prone to bugs.
*   **Recommendation:** Acknowledge the limitation. Use a high-resolution discrete step approach (e.g., "sub-stepping" movement) rather than a theoretical "continuous sweep", or clarify if a simple "BoxCast" (using a stretched AABB) is sufficient for the "Sweep" phase, followed by precise overlap checks.

## 2. Rider Side-Collisions & Stack Geometry
The proposal mentions a "Head Check" for the top-most rider but ignores side collisions.
*   **The "Wide Rider" Problem:** If a Rider is wider than the Mount, the Mount might fit through a narrow passage, causing the Rider to clip visually and logically through the walls.
*   **Inconsistency:** This contradicts the goal of being "Robust" and avoiding "corner-catching".
*   **Recommendation:** The collision check for the Root should ideally consider the **Union AABB** of the entire stack (Root + all Children). Alternatively, perform "Side Checks" for riders similar to the "Head Check", stopping the stack if *any* part of the hierarchy hits a wall.

## 3. Forced Dismount Scenarios
The dismount logic covers voluntary dismounts (failing if blocked). It fails to address **forced dismounts**.
*   **Mount Destruction:** If the Mount is destroyed (killed), the Rider *must* detach.
*   **Blocked Ejection:** If the Mount dies while the Rider is in a position where they cannot validly dismount (surrounded by walls), the proposal has no fallback.
*   **Recommendation:** Define a "Crush" or "Emergency Eject" rule. If a forced dismount is impossible due to collision, the Rider should likely take damage or be killed ("Crushed").

## 4. Determinism & Timestep
The proposal claims "100% Predictability" and uses `move_delta = velocity * dt`.
*   **Variable Timestep:** If `dt` varies (variable framerate), the simulation is non-deterministic. Floating point errors will accumulate differently.
*   **Recommendation:** Explicitly mandate a **Fixed Timestep** (e.g., 60hz fixed update loop) for the physics/movement logic to ensure true determinism.

## 5. Sliding Corner Cases
"Project remaining velocity along the wall surface" is the standard approach, but it has edge cases.
*   **Acute Corners:** Sliding into a V-shape corner can cause the entity to oscillate or get stuck if not handled (bouncing back and forth between walls in a single frame).
*   **Recommendation:** detailed logic for "Max Slide Iterations" (e.g., 3). If velocity remains after max iterations, simply zero it out to prevent jitter.
