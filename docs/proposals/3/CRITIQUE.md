# Critique of Proposal 3: Deterministic Kinematic Hierarchy

This proposal is the strongest of the three for a controlled, arcade-style game. It correctly identifies the middle ground: using Pymunk as a **Collision Detection Engine** rather than a Physics Simulator.

## 1. Strengths
*   **Precision:** By manually handling position updates via "Sweep-and-Slide", we guarantee crisp controls (instant start/stop, perfect wall sliding) that players expect in top-down games.
*   **Stability:** Removing the physics solver from the equation eliminates "exploding stacks", jittery joints, and unpredictable rotations.
*   **Simplicity:** The "Rigid Locking" hierarchy is much easier to reason about than dynamic joints.

## 2. Weaknesses & Risks

### The "Shape Sweep" Performance
*   **Cost:** Performing a `shape_query` (sweep) is more expensive than a simple point check. Doing this iteratively (2-3 times per frame for corner sliding) for *every* moving entity could be heavy if there are hundreds of entities.
*   **Implementation Complexity:** Writing a robust "Sweep-and-Slide" function that handles acute angles and "getting stuck in corners" correctly is non-trivial, even with Pymunk's help.

### The "Rider Collision" Compromise
*   **Ignored Collisions:** The proposal suggests disabling collision for riders. This means a tall stack (A->B->C) could have C clipping through a low archway or wall.
*   **Dynamic Hitbox:** Dynamically resizing the Root's hitbox to encompass children is complex (changing shapes at runtime).

## 3. Refinements Needed

### 3.1 Optimization
Instead of a full `shape_query` sweep which can be slow, we can use a **Hybrid Check**:
1.  Move X axis. Check overlap. Resolve.
2.  Move Y axis. Check overlap. Resolve.
This "Axis-Separated" movement is the gold standard for 2D platformers and top-down RPGs. It avoids the complex vector math of sliding along arbitrary normals and is extremely robust against tunneling.

### 3.2 Handling "Knockback"
The proposal focuses on "Input -> Displacement", but the game likely needs Knockback (explosions).
*   **Solution:** The `MovementController` should accumulate an `external_velocity` vector. This vector decays over time (friction).
*   **Integration:** `Total Movement = (Input * Speed) + External_Velocity`. This keeps the deterministic kinematic nature while allowing gameplay chaos.

## 4. Conclusion

This is the winning architectural path. It provides the **Control** of Proposal 2 without the **Naivety** of writing a custom collider, and the **Structure** of Proposal 1 without the **Instability** of physics joints.

**Recommendation:** Accept with the refinement of using **Axis-Separated Movement** for simpler/robust collision resolution instead of arbitrary Vector Projection sweeps.
