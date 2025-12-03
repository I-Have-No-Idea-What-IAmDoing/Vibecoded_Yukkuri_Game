# Critique of Proposal 2: Kinematic Control & "Reinventing the Wheel"

This proposal identifies the correct goal (predictable movement) but fails spectacularly in its implementation plan. It suggests abandoning a robust physics engine to write a home-brewed collision solver in Python, which is a recipe for disaster.

## 1. The "Custom Solver" Trap

The proposal suggests: *"If movement vector intersects a wall, we slide against it."*
This statement glosses over decades of complexity in computational geometry.
*   **Tunneling:** A simple position update (`pos += vel * dt`) will teleport entities through thin walls at high speeds. You need Continuous Collision Detection (CCD) or iterative stepping.
*   **The "Corner Problem":** When sliding along a wall and hitting a corner, naive slide logic often gets stuck or "pops" the entity through the geometry.
*   **Precision Errors:** Floating point errors in a custom Python solver will lead to entities vibrating against walls or slowly drifting into them.

## 2. Performance Suicide

Moving collision logic from C (Pymunk/Chipmunk) to Python is a massive performance regression.
*   **Spatial Hashing:** Pymunk uses optimized spatial hashes. Implementing a performant "Sweep Test" against all static geometry in Python every frame for every entity will kill the framerate.
*   **Garbage Collection:** Creating thousands of temporary vector objects for raycasts and slide calculations in Python will cause GC spikes.

## 3. Naive Hierarchy

The `Mount` system described is too simplistic for a robust game.
*   **Update Order Dependencies:** "Update child positions based on parent." This requires a strict graph traversal. If you update a Child before its Parent, the Child will render one frame behind, causing visual "tearing" or "jitter" that ruins the game feel.
*   **Circular Dependencies:** The proposal offers no protection against `A mounts B` and `B mounts A`, which would crash the game in an infinite loop.

## 4. Conclusion

This proposal is **rejected** not because the goal (Kinematic Movement) is wrong, but because the **implementation strategy is incompetent**. DO NOT write a physics engine in Python. Use the existing engine's *tools* (ShapeCasts/Queries) rather than rewriting its *core*.
