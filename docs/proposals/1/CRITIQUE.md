# Critique of Proposal 1: "Shape Grafting" & Pymunk Abuse

The initial proposal suggests a "Shape Grafting" approach where riders become physical extensions of the parent. While the goal of a robust stacking system is valid, the proposed implementation introduces significant architectural and gameplay risks.

## 1. Architectural Concerns

### The Risks of "Grafting"
Destructively merging physics bodies (destroying the rider's body and adding its shape to the carrier) is highly problematic:
*   **State Loss:** Destroying the body loses all current physics state (velocity, accumulated impulses).
*   **Complexity:** Managing the lifecycle of shapes and mass re-calculation is error-prone and complex to debug.
*   **Edge Cases:** Handling collisions during the transition frame (graft/ungraft) is difficult and can lead to tunneling or instability.

### Visual & Logic Desync
*   **Jitter:** Depending on the execution order of the physics step vs the render step, hard-locking the position via shape offsets can cause visual jitter.
*   **Input Handling:** If the rider is just a shape on the parent, handling separate inputs (e.g., rider shooting or throwing) becomes more convoluted as the rider is no longer a distinct physical entity.

## 2. Gameplay & Physics Interaction

### "Input vs Knockback"
The proposed `MovementSystem` fights the physics engine by manually setting velocity in a "CONTROLLED" state.
*   **Physics Fighting:** Overriding velocity (`body.velocity = target`) bypasses the solver's natural handling of collisions and friction. It makes the character feel "on rails" and can lead to weird behaviors when colliding with dynamic objects.
*   **Recommendation:** Use forces (`body.apply_force`) or a constraint-based motor for movement. This allows Pymunk to handle interactions naturally.

### The "Orphan" Problem
The proposed solution for parent death is fragile.
*   **Race Conditions:** Reconstructing a body in the same frame a parent is destroyed is risky.
*   **Overlaps:** Spawning the rider exactly where the parent was can cause immediate penetration issues.

## 3. Constructive Recommendation: Constraint-Based System

Instead of "Shape Grafting", the proposal should be revised to use **Physics Constraints (Joints)**.
*   **PivotJoint:** Use a `pymunk.PivotJoint` (or PinJoint) to attach the rider to the carrier. This keeps them as separate physical bodies.
*   **Advantages:**
    *   **No Destruction:** Rider keeps its body, mass, and properties. No state loss.
    *   **Automatic Interaction:** Pymunk solves the motion. The rider naturally follows the carrier.
    *   **Flexibility:** We can adjust the joint's stiffness or damping to allow for "wobble" or tight locking.
    *   **Easy Dismount:** Just remove the joint. The rider preserves its momentum.
    *   **Orphan Safety:** If the parent dies, the joint is automatically invalidated or can be easily removed, leaving the rider free.

## 4. Conclusion

The proposal requires significant revision. The "Shape Grafting" approach should be abandoned in favor of a **Constraint-based Mount System**. The movement logic should be simplified to work *with* Pymunk (forces/impulses) rather than overriding it.
