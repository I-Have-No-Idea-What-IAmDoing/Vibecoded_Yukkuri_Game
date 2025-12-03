# Critique of Proposal 2: Kinematic Control & "Reinventing the Wheel"

The proposal correctly identifies that standard dynamic physics can feel "floaty" for precise character movement, but the proposed solution of rewriting collision resolution in Python is ill-advised.

## 1. The "Custom Solver" Risk

The proposal suggests: *"If movement vector intersects a wall, we slide against it."*
*   **Complexity:** Implementing robust collision response (handling internal corners, acute angles, tunneling) is difficult and error-prone.
*   **Performance:** Moving the heavy lifting of collision detection and resolution from Pymunk's C-based engine to Python loops will likely degrade performance significantly, especially with many entities.

## 2. Pymunk is already Capable

Pymunk supports **Kinematic Bodies**. These are bodies that are moved manually (infinite mass) but still interact with the spatial index and can push other dynamic bodies.
*   The proposal says "Make PhysicsBody kinematic (sensor only)". This is a misunderstanding. Kinematic bodies *can* have shapes and collisions.
*   We can use Pymunk to handle the "slide" logic or simply use a dynamic body with very high friction/damping and manual velocity control (as suggested in the revised Proposal 1).

## 3. Hierarchy & Mounting

The `Mount` system description has valid points but misses key implementation details.
*   **Graph Traversal:** The proposal mentions "Iterate over all entities". To prevent frame-behind lag, the transform update must strictly follow the hierarchy (Roots first, then children). A flat iteration might update a child before its parent has moved.
*   **Cycles:** There is no check for circular dependencies (A rides B, B rides A).

## 4. Constructive Recommendation

We should **not** rewrite the physics solver. Instead, we should leverage Proposal 1's "Constraint-Based" approach for mounting. It naturally handles the hierarchy without manual position syncing and prevents lag.

However, if "Kinematic" movement is truly desired (for pixel-perfect controls like an RPG), we should still use Pymunk's facilities:
*   Use a **Dynamic Body** with high damping (as per Proposal 1) for the best balance of responsiveness and physical interaction.
*   Use **Constraints** for mounting.

The "Kinematic Movement System" as described (manual slide collision in Python) should be abandoned. The "Mounting System" should be merged into the Constraint-based approach of Proposal 1.

## 5. Conclusion

This proposal is **rejected** in favor of Proposal 1 (Revised). Proposal 1 solves the "Stacking/Mounting" problem more robustly using Constraints. The "Floaty Movement" problem is better solved by tuning the physics parameters (damping/force) rather than abandoning the physics engine.

However, for the sake of this exercise, I will revise this proposal to focus *specifically* on a **Kinematic Character Controller** that uses Pymunk's `Body.KINEMATIC` correctly, rather than a custom Python solver, and how it interacts with the Constraint system.
