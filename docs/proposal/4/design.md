# Design: Pragmatic Movement Polish

## 1. Introduction

Previous proposals have advocated for high-risk, high-complexity rewrites of the core movement system. This proposal rejects that approach. It argues that the desired "game feel" and stat integration can be achieved with minimal architectural changes, focusing on animation and tuning rather than radical physics model alterations. The goal is to make the Yukkuris feel "bouncy" and alive without sacrificing the stability and predictability of the existing physics-based movement.

## 2. Core Philosophy

*   **Animation-Driven Feel**: The "hopping" of a Yukkuri is a visual and timing effect, not a physics simulation. The underlying movement should remain predictable and controllable.
*   **Decouple Aesthetics from Logic**: The system that makes movement *look* good should be separate from the system that makes it *work*.
*   **Stability First**: Preserve the existing, working, and deterministic `Pymunk`-based movement foundation. Do not introduce indeterminism for the sake of aesthetics.
*   **Iterative Refinement**: The changes should be incremental and easily tunable.

## 3. Proposed Architecture

The proposal introduces one new component and one new system, and refines an existing AI action.

### 3.1. New Components

#### `Locomotion` (State & Tuning)
This component acts as a central hub for movement-related parameters and state, but it does *not* contain complex state machines.
```python
@dataclass
class Locomotion:
    # --- Tuning Parameters (Set by StatSyncSystem) ---
    # The maximum speed the entity should move at, derived from stats.
    max_speed: float = 100.0
    # How quickly the entity accelerates, derived from stats.
    acceleration: float = 200.0
    # Multiplier for the "hop" animation speed and height.
    hop_enthusiasm: float = 1.0 # (0.0 to 2.0)

    # --- Animation State ---
    # Is the entity currently trying to move?
    is_moving: bool = False
    # Timer to drive the hop animation cycle (0.0 to 1.0).
    hop_timer: float = 0.0
```

#### `Renderable` (Existing, but with additions)
We add a field to the existing `Renderable` component to allow the `AnimationSystem` to apply visual offsets without fighting the `RenderSystem`.
```python
@dataclass
class Renderable:
    # ... existing fields like sprite, scale, etc.
    visual_offset: Vector2 = Vector2(0, 0)
```

### 3.2. New System

#### `AnimationSystem`
This system is purely for aesthetics. It runs after the AI and Physics systems.
-   **Input**: `Locomotion`, `Renderable`, `PhysicsBody`
-   **Logic**:
    1.  Read `Locomotion.is_moving`. If `True`, increment `Locomotion.hop_timer`.
    2.  Based on `hop_timer`, calculate a vertical offset (`y_offset`) using a sine wave or parabolic curve to simulate a hop. The amplitude of this wave is controlled by `Locomotion.hop_enthusiasm`.
    3.  Apply this offset to `Renderable.visual_offset.y`.
    4.  Apply squash and stretch to `Renderable.scale` based on the phase of the hop (squash at the start/end, stretch at the apex).
    5.  This system *never* modifies physics. It only changes how the entity is drawn.

### 3.3. Refined AI Action

#### `MoveToTarget`
The `MoveToTarget` action is simplified and refactored to be a better citizen.
-   **Old Logic**: Calculates path, steering, and directly sets velocity.
-   **New Logic**:
    1.  It still calculates the desired steering velocity towards a target.
    2.  It reads `Locomotion.max_speed` and `Locomotion.acceleration` to determine the final target velocity.
    3.  It applies this velocity to the `PhysicsBody`. This can be done via `body.velocity` for direct control, or by applying a force to accelerate towards the target velocity for a "weightier" feel. Using force is preferable as it respects mass.
    4.  It sets `Locomotion.is_moving = True` when it's actively trying to move, and `False` when it has arrived or failed.

### 3.4. Stat Integration

A simple, infrequent `StatSyncSystem` is introduced to bridge game stats to movement parameters.
-   **Input**: `YukkuriStats`, `Locomotion`
-   **Logic**: (Runs once every second or on stat change events)
    -   If `YukkuriStats.energy` is low, decrease `Locomotion.max_speed` and `Locomotion.hop_enthusiasm`.
    -   If `YukkuriStats.age` is `BABY`, increase `hop_enthusiasm` but keep `max_speed` low.
    -   This keeps the high-frequency `MoveToTarget` and `AnimationSystem` loops free from complex stat calculations.

## 4. Rationale

*   **Low Risk**: This design doesn't touch the core physics simulation loop. The movement remains predictable and based on the stable `Pymunk` engine. If the animation system has bugs, the game is still playable; the visuals will just be glitchy.
*   **Solves the "Feel" Problem**: The "hopping" is achieved visually, which is what "game feel" is. The player sees a bouncing Yukkuri. The underlying mechanics can remain simple and robust.
*   **Tunable**: `max_speed`, `acceleration`, and `hop_enthusiasm` are simple, intuitive knobs that designers can tweak to get the exact feel they want for different Yukkuri types and states.
*   **Clear Separation of Concerns**:
    -   `MoveToTarget` (AI) decides the *direction* and *intent*.
    -   `Locomotion` (Data) holds the *parameters* and *state*.
    -   `PhysicsSystem` (Engine) executes the *movement*.
    -   `AnimationSystem` (Visual) creates the *aesthetic*.

This design provides a clear, low-risk path to achieving the project's aesthetic goals without jeopardizing the project's stability or creating an unmaintainable mess.