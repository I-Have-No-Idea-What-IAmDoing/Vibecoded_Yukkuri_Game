# Critique: Force-Based Hopping Movement System (Proposal 2)

This proposal is a classic case of a developer falling in love with a "cute" idea without any regard for the technical nightmare it will create or the negative impact it will have on gameplay. It mistakes physical simulation for good game design, and in its quest for "realism," it guarantees a glitchy, frustrating, and un-fun experience.

## 1. You Are Making a 2D Game. Stop Fighting It.
The single most egregious flaw here is the "Z-Axis Simulation." You are proposing to bolt a crude, manually-coded 3D gravity simulation onto a sophisticated 2D physics engine. This is, without exaggeration, a recipe for disaster. You will spend months chasing down bugs where a Yukkuri's 2D collision box (managed by Pymunk) interacts with the world in a way that completely contradicts its fake 3D position (managed by your hacky Euler integration). Can a Yukkuri "hop over" a low wall? If the 2D collision box hits the wall, Pymunk will stop it. If your Z-height says it's "in the air," the sprite will float above the wall it's stuck on. This is how you create a game that feels fundamentally broken.

## 2. Hopping is Not Fun. It is Annoying.
The design romanticizes the idea of "hopping" without considering the player experience.
-   **Imprecision is Frustrating**: AI-controlled characters that are locked into ballistic arcs will constantly overshoot their destinations. They will fail to pick up items, fail to interact with other characters, and generally look incompetent.
-   **Unresponsive Controls**: The "hop cycle" introduces mandatory delays (pre-hop, landing recovery). This means that a Yukkuri cannot react instantly to new threats or opportunities. For a simulation game that relies on observing emergent behavior, this will make the creatures feel sluggish and stupid.
-   **Visual Noise**: Constant bouncing is visually distracting. It makes it harder for the player to track individual characters and assess the state of the game at a glance.

## 3. The "Stat-Driven" Ruse
The proposal claims that coupling movement to a dozen different stats (`Agility`, `Health`, `Fullness`, etc.) will create deep, emergent gameplay. In reality, it will create an untunable mess. When a Yukkuri's movement feels wrong, where do you look? Is the impulse too low? Is the mass too high? Is the `Fullness` modifier miscalibrated? Is the `Athleticism` score not being calculated correctly? By creating this complex web of interdependencies, you are making it impossible to reason about and tune the most fundamental system in your game. This isn't depth; it's just complexity.

## 4. Physics Realism is a Trap
The argument that "Force-Based" is better because "it respects mass" is a red herring. Games are not about physical accuracy; they are about creating a believable and controllable experience. Directly setting velocity is predictable, easy to debug, and gives you precise control over your character's movement. It is the correct tool for the job 99% of the time. Sacrificing that control for the sake of "realism" in a game about sentient bean paste buns is a foolish trade.

---

# Revise

The goal—to make the Yukkuris *feel* like they are hopping—is a good one. The implementation is the problem. The solution is to treat movement as a solved problem and hopping as a purely **visual and aesthetic** layer on top.

## 1. Separate Model from View
The core of the problem is confusing how something *looks* with how it *works*.
-   **Model (The Truth)**: The Yukkuri's position and collision should be managed by a simple, reliable, 2D velocity-based system. It slides from A to B. This is the "truth" that the pathfinding, AI, and collision systems care about.
-   **View (The Illusion)**: The sprite's rendering position should be offset from the model's position. This is where you implement the "hop."

## 2. Implement a Visual "Hop"
Create a new component, `VisualBob`, with a single field: `timer`.

```python
@dataclass
class VisualBob:
    timer: float = 0.0
    bob_height: float = 10.0
    bob_speed: float = 5.0
```

In your rendering system, calculate a vertical offset using a sine wave:
`render_y = model_y - abs(sin(visual_bob.timer * visual_bob.bob_speed)) * visual_bob.bob_height`

When the Yukkuri is moving, increment the timer. When it stops, reset it. That's it. You now have a bouncing, hopping animation that is completely decoupled from the physics.

## 3. Use Animation for Everything Else
-   **Squash and Stretch**: This is an animation. Trigger a "landing" animation when the character stops moving, and a "prepare to move" animation when it starts. Don't tie it to a physics state machine.
-   **Dust Particles**: This is a particle effect. Trigger it when the character's `is_moving` flag changes from `True` to `False`.

## 4. Keep Stats in the AI Layer
If you want a tired Yukkuri to move slower, the `YukkuriStats` component should affect the *target speed* that the AI requests. The AI asks to move at 50% speed; the movement system then reliably moves the character at that speed. This keeps the concerns separate: stats influence AI decisions, and AI decisions command a predictable movement system. Do not let stats directly manipulate physics parameters.
