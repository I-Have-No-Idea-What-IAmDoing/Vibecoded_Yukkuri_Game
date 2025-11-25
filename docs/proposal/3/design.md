# Design: A Simple, Kinematic Movement System

## 1. Introduction

After reviewing previous proposals, it's clear that attempts to simulate hopping with complex physics have led to overly complicated, difficult-to-tune, and bug-prone designs. This proposal presents a final, simplified approach that achieves the desired aesthetic of "hopping" without compromising the stability, controllability, and debuggability of the movement system.

## 2. Core Philosophy: Direct Control, Visual Flair

This design is built on two core principles:

1.  **Movement is Kinematic:** The underlying movement of a Yukkuri is a solved problem. We will use a direct, velocity-based approach. The AI decides how fast and in what direction the entity should move, and the physics body is set to that velocity. This is predictable, reliable, and easy to control.
2.  **Hopping is a Visual Effect:** The "bouncy" feel is a purely aesthetic layer. It is completely decoupled from the actual 2D movement logic, preventing physics glitches and ensuring the AI can navigate precisely.

## 3. The `MovementController` Component

We will consolidate all movement-related data and control into a single component. This replaces the need for `MovementRequest`, `Locomotion`, and multiple complex systems.

```python
@dataclass
class MovementController:
    """A simple component that holds movement commands and visual state."""
    # The velocity requested by the AI for the current frame
    target_velocity: Vector2 = Vector2(0, 0)

    # --- Visual Tuning ---
    # Manages the animation of the visual hop
    visual_bob_timer: float = 0.0
    bob_height: float = 10.0
    bob_speed: float = 5.0
```

## 4. Architecture: AI in Command

The architecture is radically simplified. The AI has direct, imperative control over movement on a frame-by-frame basis. There are no complex, asynchronous systems.

### 4.1. AI / Behavior Tree Responsibility
The `MoveToTarget` action (or similar AI logic) is the single source of truth for movement intent. In each tick, it performs the following:

1.  **Consults Stats:** It directly reads the `YukkuriStats` component (e.g., energy, health, weight).
2.  **Calculates Velocity:** It determines the desired direction and calculates a final `target_velocity`, factoring in the stat modifiers. For example, low energy results in a lower speed.
3.  **Issues Command:** It gets the entity's `MovementController` component and sets its `target_velocity`.

```python
# Conceptual logic within the Behavior Tree
speed_modifier = calculate_speed_from_stats(entity.stats)
direction = (target_position - entity.position).normalized()
final_velocity = direction * max_speed * speed_modifier

entity.movement_controller.target_velocity = final_velocity
```

### 4.2. `MovementSystem`
A single, extremely simple system runs each frame to execute the AI's command.

**Logic per Entity:**
1.  **Apply Velocity:** `physics_body.velocity = movement_controller.target_velocity`
2.  **Update Visuals:** `movement_controller.visual_bob_timer += dt * physics_body.velocity.length()`

### 4.3. Rendering System
The rendering system uses the `visual_bob_timer` to create the hop illusion, identical to the revised Proposal 2. A vertical offset is applied to the sprite's `y` position using a sine wave, making it bounce as it moves.

## 5. Addressing All Previous Critiques
This design provides the definitive solution by:

*   **Eliminating Complexity:** It removes the need for multi-system pipelines, implicit state machines (`LocomotionSystem`), and unnecessary middleware (`StatSyncSystem`). The flow of data is direct and simple: `AI -> Component -> System`.
*   **Ensuring Controllability:** By using a kinematic approach, the overshooting and pathfinding problems of force-based systems are completely avoided. The Yukkuri moves exactly where the AI tells it to.
*   **Prioritizing Debuggability:** When movement is wrong, the cause is clear. Either the AI calculated the wrong velocity, or the simple `MovementSystem` failed to apply it. There is no black box of "cyclic drag" or a distributed state to untangle.
*   **Achieving the Aesthetic:** The desired "bouncy" feel is achieved through a simple, decoupled visual effect that is easy to tune and cannot break the core gameplay logic.
