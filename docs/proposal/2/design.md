# Design: Visual Hopping for Yukkuri Movement

## 1. Introduction
The current Yukkuri movement system, which directly sets entity velocity, is functionally robust and predictable. However, it lacks the characteristic "bouncy" or "hopping" aesthetic that would give the creatures more personality. The goal is to add this visual flair without sacrificing the stability and control of the existing system.

This proposal outlines a plan to implement a purely **visual hopping effect** that is completely decoupled from the underlying physics and movement logic. We will enhance the "view" without altering the "model."

## 2. Core Principle: Separate Model from View

The fundamental flaw in previous considerations was confusing how a Yukkuri *should look* with how it *should work*. This design strictly separates the two:

-   **The Model (The Truth):** The Yukkuri's position, collision, and movement logic will continue to be managed by a simple and reliable 2D, velocity-based system. For all purposes of AI, pathfinding, and physics, the Yukkuri slides smoothly from point A to point B. This is the "truth" of the simulation.
-   **The View (The Illusion):** The sprite's rendered position will be visually offset from the model's true position to create the *illusion* of a hop. This allows for rich, aesthetic motion without creating bugs or gameplay issues.

## 3. Proposed Design

### 3.1. The `VisualBob` Component
We will introduce a new, simple component to manage the hopping aesthetic.

```python
@dataclass
class VisualBob:
    """Manages the state for a purely visual vertical bobbing effect."""
    timer: float = 0.0
    bob_height: float = 10.0 # Max pixels to offset the sprite vertically
    bob_speed: float = 5.0  # How fast the bobbing cycle runs
```

A system will be responsible for updating this component's timer. When the entity's physics body has a non-zero velocity, the `timer` will be incremented. When the entity stops, the `timer` will be reset to zero.

### 3.2. Rendering System Update
The rendering system will be modified to use this component.

-   **Logic:** When drawing an entity that has a `VisualBob` component, it will calculate a vertical offset.
-   **Calculation:** `render_y = model_y - abs(sin(visual_bob.timer * visual_bob.bob_speed)) * visual_bob.bob_height`
-   **Result:** This will cause the sprite to bounce up and down using a smooth sine wave as the entity moves, completely independent of the actual 2D physics simulation. The `model_y` remains the ground truth for collision.

### 3.3. Animation and Effects
The "hop cycle" will be represented by animations and particle effects, triggered by changes in the model's state, not a complex physics state machine.

-   **Squash and Stretch:** These are animations.
    -   A "prepare to move" animation (squash) can be triggered when the AI decides to move but before velocity is applied.
    -   A "landing" animation (squash then settle) can be triggered when the entity's velocity changes from non-zero to zero.
-   **Dust Particles:** This is a particle effect. It will be triggered at the entity's position when its state changes to "stopped."

### 3.4. Stat Integration
Stats like `Health` or `Energy` should not directly manipulate physics. Instead, they will influence the AI's high-level decisions.

-   **AI Layer:** The AI reads the `YukkuriStats` component. A tired or injured Yukkuri's AI will simply request a lower `target_speed`.
-   **Movement System:** The movement system receives this `target_speed` and predictably moves the entity at that speed.

This maintains a clear separation of concerns: stats influence AI decisions, and the AI commands a reliable movement system.

## 4. Benefits
*   **Robust and Bug-Free:** By not creating a fake Z-axis or fighting the 2D physics engine, we avoid a massive category of potential physics and collision bugs.
*   **Visually Appealing:** We achieve the desired "bouncy" game feel without any negative impact on gameplay.
*   **Controllable and Tunable:** Movement remains precise and easy to debug. The visual hop effect (`bob_height`, `bob_speed`) can be tuned independently by artists without affecting game logic.
*   **Responsive:** Since the underlying movement is continuous, Yukkuris can react instantly to new commands from the AI, making them feel more intelligent and alive.
