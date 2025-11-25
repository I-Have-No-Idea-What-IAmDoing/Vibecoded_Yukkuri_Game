# Rationale for Movement System Overhaul

## 1. Current State Analysis
The current movement implementation in `yukkuri_game` is functional but rudimentary.
- **Mechanic**: `MoveToTarget` calculates a steering velocity and directly overwrites `PhysicsBody.velocity`.
- **Feel**: The entities "slide" across the map with constant friction. There is no sense of mass or biomechanics.
- **Disconnect**: Movement speed is largely hardcoded or arbitrary (`speed=100.0` default). It does not reflect the internal state of the Yukkuri (tired, hungry, injured, baby vs adult).

## 2. Why "Hopping"?
Yukkuris are canonically depicted as "manjuu" (steamed buns) that move by hopping or bouncing.
1.  **Immersion**: Sliding buns break suspension of disbelief. Hopping is their defining locomotor trait.
2.  **Rhythm**: Hopping introduces a "cadence" to movement. Instead of continuous position updates, there are bursts of action. This changes how players predict and intercept them.
3.  **Physics Interaction**: A hopping entity interacts with physics objects differently. It applies force on landing, potentially knocking things over, whereas a slider just pushes.

## 3. Why Force-Based?
Directly setting velocity (`body.velocity = v`) breaks the physics simulation loop.
-   **Collision Resolution**: If a velocity-set body hits a wall, Pymunk resolves it, but the next frame we overwrite it again, causing jitter or "tunneling".
-   **Mass**: Pymunk simulates mass, but setting velocity ignores it. Force/Impulse respects mass ($F=ma$). A fat Yukkuri needs more force to move, or moves slower for the same force. This comes "for free" with forces.

## 4. Why Stat Integration?
A simulation game thrives on the connectivity of its systems.
-   **Consequences**: If a Yukkuri starves, it should get slow. If it runs a marathon, it should get tired.
-   **Diversity**: Not all Yukkuris should move the same. Athletic ones should be faster; lazy ones slower.
-   **Feedback Loop**: Players can visually *see* the state of a Yukkuri by how it moves, reducing the need for UI/Health bars.

## 5. Conclusion
This overhaul is not just visual polish; it is a fundamental deepening of the simulation mechanics. It aligns the code with the thematic identity of the entities and opens up design space for gameplay (stamina management, terrain costs, physical interactions).
