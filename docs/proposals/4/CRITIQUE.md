# Critique of Proposal 4: Deterministic Kinematic Hierarchy

## 1. Collision Detection: Raycast Bundle vs. Shape Sweep
The proposal suggests using a "Raycast Bundle" (casting rays from corners and center) to detect collisions. While faster than full physics simulation, this approach has significant flaws:
*   **Tunneling/Clipping:** Sparse rays can miss small obstacles (e.g., spikes, thin poles) that fit between the rays.
*   **Corner Cases:** Rays from corners might catch on geometry in unexpected ways or miss corners when sliding.
*   **Shape Mismatch:** This approximates the entity as a set of lines rather than a solid shape. A box shape moving diagonally is effectively a hexagon swept area, which 3-5 rays do not represent accurately.

**Recommendation:** Replace "Raycast Bundle" with **Shape Casting** (sweeping the actual collider shape along the movement vector). `pymunk.Space.shape_query` or iterating with a shape test at discrete steps is much more robust and ensures "100% Predictability" without visual clipping.

## 2. "Riders don't have collision" Simplication
The proposal states that "Riders don't have collision" and that the "Parent is the only physical agent".
*   **Gameplay Limitation:** This prevents riders from taking damage from projectiles, blocking enemies, or hitting low ceilings.
*   **Visual Weirdness:** Tall stacks will clip through environment geometry (ceilings, overhangs).

**Recommendation:** Riders should likely retain **Sensor** shapes (to detect hits) or contribute to a **Compound Shape** for the Root (so the entire stack collides with the world). At minimum, a "Head Check" raycast for the top-most rider is needed to prevent ceiling clipping.

## 3. Dismounting Logic
"Spiral Search" or "Ejecting" for dismounting is vague and can introduce non-determinism or buggy behavior (teleporting into walls).
*   **Unpredictability:** If the spiral search finds different spots based on float precision or order of operations, it violates the core goal.

**Recommendation:** Define a strict, deterministic rule for dismounting. E.g., "Dismount always attempts strict relative offsets (Left, Right, Back). If all blocked, dismount fails."

## 4. Dirty Flag Logic
"Only process the hierarchy for a Root if it has successfully moved this frame."
*   **Missing Cases:** This misses cases where a parent *rotates* but doesn't change position, or when the hierarchy structure changes (a child is added/removed) without movement.
*   **Animation:** If visual attachments rely on this system, they might need updates even if the physics body is stationary (e.g., idle animation sway).

**Recommendation:** The dirty flag should track "Transform Change" (Position OR Rotation) and "Hierarchy Change" (Child Added/Removed).

## 5. Broadphase Optimization
Using `pymunk.Space.bb_query` is a good start, but it returns all shapes in the box.
*   **Filtering:** The proposal needs to explicitly mention filtering. We don't want to stop movement because of a Trigger or a Coin.

**Recommendation:** Explicitly state that queries must filter for "Obstacle" collision types only.
