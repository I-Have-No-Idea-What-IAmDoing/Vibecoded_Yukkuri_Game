# Critique of Proposal 2: The "Fighting the Engine" Anti-Pattern

This proposal tries to have its cake and eat it too, resulting in a fractured system that works against the physics engine rather than with it.

## 1. Velocity Override on Dynamic Bodies

The proposal suggests: *"We maintain the entity as a Dynamic Body... but effectively override its behavior... set body.velocity directly."*

*   **Destabilizing the Solver:** Pymunk's solver expects velocity to change due to forces and impulses. Manually overwriting velocity every frame (`body.velocity = target`) effectively gives the object infinite mass for that frame. When it hits a wall, the solver tries to resolve the collision, but the next frame you overwrite it again. This causes jitter, tunneling, and "vibrating against walls."
*   **Physics Fighting:** If an explosion pushes the character (External Force), and your input logic sets velocity (Input Override), who wins? The proposal suggests a "Knockback Threshold" state machine. This is brittle. You end up writing a complex priority system just to decide if the physics engine is allowed to work.

## 2. "High Friction" Hack

The suggestion to use "High Friction/Damping" to stop movement is a magic number hack.
*   **Inconsistent Stopping:** Friction depends on the surface. If the character walks on "ice" vs "grass", the stopping time changes, messing up the "snappy" feel.
*   **Tunneling:** High velocity changes combined with forced stops are a prime cause of physics tunneling (passing through walls).

## 3. The "Hybrid" Fallacy

The proposal claims to solve the "floaty" problem of Prop 1 and the "complexity" of Prop 3. In reality, it combines the **instability** of Prop 1 (using dynamic bodies for control) with the **hackiness** of Prop 3 (manual overrides).

*   **Joints are still Jelly:** It retains the Constraint System from Proposal 1, so the stack is still a wobbling mess.
*   **Input Lag:** Interpolating velocity (`interpolate_to`) adds input lag. Players want instant response.

## 4. Conclusion

This proposal is a collection of hacks. Overriding velocity on dynamic bodies is a known "code smell" in physics integration. It leads to a character that jitters against walls and ignores game physics when you don't want it to. **Rejected.**
