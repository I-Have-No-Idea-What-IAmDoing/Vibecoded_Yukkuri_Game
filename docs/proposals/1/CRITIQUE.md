# Critique of Proposal 1: The "Ice Skating" Simulator

This proposal is a recipe for a game that feels terrible to play. It sacrifices gameplay precision for the sake of "pure" physics simulation, a common trap for developers who mistakenly believe that "realism" equals "fun".

## 1. Force-Driven Movement: The "Floaty" Nightmare

The proposal advocates for applying forces (`force += move_input * speed`) and relying on damping to stop.
*   **Lack of Precision:** Players expect to stop when they release the stick. Force-based movement introduces inertia that makes the character slide like a hovercraft. Trying to tune "damping" to fix this results in a character that feels like it's moving through molasses.
*   **Cornering:** Making sharp turns with force-based movement is sluggish. You have to wait for the old velocity to bleed off while the new force takes effect. This is acceptable for a space lander game, not a character controller.
*   **Unpredictability:** Variable timesteps or slight physics glitches can make movement non-deterministic. Speedrunners and precision players will hate this.

## 2. Constraints for Stacking: The "Jelly Tower"

Using `PivotJoint` for stacking is architecturally lazy and visually unstable.
*   **Wobble:** A stack of physics bodies connected by joints is essentially a system of springs. No matter how stiff you make the joints, a stack of 4+ entities *will* wobble. It looks cheap and buggy.
*   **The "Heavy Head" Problem:** If the top entity hits a wall, the torque is transferred down the chain, causing the bottom entity (the player) to spin or flip unpredictably. You'll spend weeks tweaking mass ratios and moments of inertia trying to fix this, and it will still break.
*   **Infinite Force Errors:** When a stack gets crushed or pulled apart, joints can generate massive impulse spikes to correct errors, sending entities flying off the map.

## 3. Complexity Overload

The proposal introduces `MountSystem`, `ShapeFilter` groups, and `EntityDestroyed` listeners just to make two sprites stick together.
*   **Over-Engineering:** We are building a game about cute creatures stacking, not simulating a bridge suspension system.
*   **Orphan Logic:** The logic to handle "parent death" by breaking joints and applying "tumble impulses" adds unnecessary state complexity.

## 4. Conclusion

This proposal prioritizes *physics correctness* over *game feel*. It will result in a sloppy, imprecise game where the player fights the controls and the stack acts like a wet noodle. **Rejected.**
