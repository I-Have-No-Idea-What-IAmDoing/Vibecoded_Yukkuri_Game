# Implementation Plan: A Simple, Kinematic Movement System

This document outlines the actionable tasks required to implement the simplified, kinematic movement system as described in `design.md`. The focus is on direct AI control and a decoupled visual hopping effect.

## Phase 1: Core Component and System

1.  [ ] **Define `MovementController` Component**
    -   Create the `MovementController` dataclass in a central components file (e.g., `src/yukkuri_game/game/components.py`).
    -   **Fields**:
        -   `target_velocity: Vector2`
        -   `visual_bob_timer: float`
        -   `bob_height: float`
        -   `bob_speed: float`
    -   *Verification*: The component can be added to an entity.

2.  [ ] **Update Entity Factory**
    -   Modify the `YukkuriFactory` to attach the new `MovementController` component to all Yukkuri entities. Remove any old movement-related components.

3.  [ ] **Create `MovementSystem`**
    -   Create a new, simple system at `src/yukkuri_game/game/systems/movement_system.py`.
    -   **Logic per frame**:
        1.  Get the `MovementController` and the `PhysicsBody` for an entity.
        2.  Set the body's velocity directly: `physics_body.velocity = movement_controller.target_velocity`.
        3.  Update the visual timer based on actual movement: `movement_controller.visual_bob_timer += dt` if velocity is non-zero.
        4.  Reset `movement_controller.target_velocity` to zero at the end of the update so the entity stops if the AI doesn't issue a new command.
    -   Register the `MovementSystem` in the main game loop. It should run after the AI systems but before the main physics step.

## Phase 2: AI Refactoring

4.  [ ] **Refactor `MoveToTarget` Behavior Tree Action**
    -   This is the most critical change. The `MoveToTarget` action's `update` method must now perform the full velocity calculation every tick.
    -   **Logic**:
        1.  Determine the direction to the target.
        2.  Fetch the `YukkuriStats` component.
        3.  Calculate a speed based on stats (e.g., energy, health).
        4.  Combine direction and speed to get a final `target_velocity` vector.
        5.  Get the entity's `MovementController` and set `movement_controller.target_velocity = final_velocity`.
    -   The action will return `RUNNING` as long as it's active, `SUCCESS` when the destination is reached, and `FAILURE` if it can't find a path.

5.  [ ] **Refactor Other AI Actions**
    -   Update any other behaviors that cause movement (e.g., `Wander`, `Flee`) to follow the same pattern of calculating a final velocity and setting it in the `MovementController`.

## Phase 3: Visual Integration

6.  [ ] **Modify the Rendering System**
    -   In the main `RenderSystem`, check for the `MovementController` component on each entity.
    -   If found, calculate the vertical "hop" offset using the `visual_bob_timer`: `offset_y = abs(sin(controller.visual_bob_timer * controller.bob_speed)) * controller.bob_height`.
    -   Render the entity's sprite at `y - offset_y`. The entity's true position remains unchanged.
    -   Optionally, render a shadow at the entity's true `y` position to ground it visually.

## Phase 4: Cleanup and Verification

7.  [ ] **Remove All Deprecated Code**
    -   Thoroughly delete all components, systems, and utilities related to previous, more complex movement designs. This includes `MovementRequest`, `Path`, `SteeringAgent`, `Locomotion`, `NavigationSystem`, and `SteeringSystem`. The goal is to leave only the simple, new architecture in place.

8.  [ ] **Testing and Tuning**
    -   Perform extensive playtesting to verify that movement is predictable and responsive.
    -   Confirm that Yukkuris with different stats (e.g., low energy) move at visibly different speeds.
    -   Tune the `bob_height` and `bob_speed` parameters to achieve a pleasant visual effect.
    -   Ensure there are no physics bugs or weird interactions resulting from the visual offset.
