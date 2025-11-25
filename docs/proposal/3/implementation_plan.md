# Revised Implementation Plan: A Simple, Kinematic Movement System

This document provides a robust, test-driven plan for implementing the kinematic movement system. It addresses the critiques of the previous plan by emphasizing incremental refactoring, automated testing, and correct system logic.

## Phase 1: Foundational Components and Configuration

1.  [ ] **Externalize Movement Parameters**
    -   Create a central data asset or configuration file (e.g., `data/yukkuri_tuning.json`) to store movement-related visual parameters.
    -   **Fields**: `bob_height`, `bob_speed`.
    -   *Verification*: The configuration can be loaded successfully by the game.

2.  [ ] **Define `MovementController` Component**
    -   Create the `MovementController` dataclass in `src/yukkuri_game/game/components.py`.
    -   **Fields**:
        -   `target_velocity: Vector2`
        -   `visual_bob_timer: float`
    -   Populate `bob_height` and `bob_speed` from the configuration file upon component creation.
    -   *Verification*: The component is created with values from the tuning file.

3.  [ ] **Create and Test `MovementSystem`**
    -   Create the new system at `src/yukkuri_game/game/systems/movement_system.py`.
    -   **Logic**:
        1.  `physics_body.velocity = movement_controller.target_velocity`
        2.  `movement_controller.visual_bob_timer += dt * physics_body.velocity.length()`
    -   **Crucially, this system does NOT reset `target_velocity`. The AI is responsible for stopping.**
    -   *Verification*:
        -   **Integration Test**: Create a test scene with an entity possessing a `PhysicsBody` and `MovementController`. The test will manually set `target_velocity`, run the `MovementSystem`, and assert that `physics_body.velocity` is updated correctly and the `visual_bob_timer` is advanced proportionally to the velocity.

4.  [ ] **Update Entity Factory**
    -   Modify the `YukkuriFactory` to attach the `MovementController` to new Yukkuris.

## Phase 2: Incremental AI Refactoring and System Replacement

5.  [ ] **Refactor and Unit Test `MoveToTarget` Action**
    -   Modify the `MoveToTarget` behavior tree action.
    -   **Logic**:
        1.  Calculate the desired velocity based on stats and target direction.
        2.  Set `movement_controller.target_velocity` to the calculated value.
        3.  When the target is reached, **explicitly set `target_velocity` to `Vector2(0, 0)` to stop.**
    -   *Verification*:
        -   **Unit Test**: Write a test that provides a mock entity with stats and a target position to the `MoveToTarget` action. Assert that the `target_velocity` set in the `MovementController` is correct for various inputs (e.g., low energy, different distances).

6.  [ ] **Integration Test and Deprecate Old Navigation**
    -   *Verification*:
        -   **Integration Test**: Run a test scene where a Yukkuri AI using the refactored `MoveToTarget` successfully navigates to a point.
    -   Once verified, **delete** the old `NavigationSystem`, `SteeringSystem`, `Path`, and `SteeringAgent` components and systems. This constitutes the first incremental cleanup.

7.  [ ] **Refactor `Wander` and `Flee` Actions**
    -   Repeat the refactoring process for any other movement-related AI actions, ensuring they also take full control of setting the `target_velocity`, including stopping.
    -   *Verification*: Add unit tests for their respective velocity calculations.

## Phase 3: Visual Integration and Final Cleanup

8.  [ ] **Implement Visual Hop in `RenderSystem`**
    -   Modify the `RenderSystem` to use the `visual_bob_timer`, `bob_height`, and `bob_speed` from the `MovementController` to apply a sinusoidal vertical offset to the sprite's render position.
    -   Render a shadow at the entity's true ground position (`physics_body.position`).
    -   *Verification*: Manual playtesting to confirm the visual "hop" is working as intended and is tunable by changing the values in the configuration file.

9.  [ ] **Final Cleanup**
    -   Perform a final search for and remove any remaining obsolete movement code, such as `MovementRequest`, `Locomotion`, etc.
    -   *Verification*: The project builds and all tests pass. The only movement system is the new, simplified one.

## Phase 4: Final Testing

10. [ ] **End-to-End Verification**
    -   Perform a final round of playtesting to confirm all movement behaviors are correct, responsive, and visually appealing.
    -   Confirm that stat-based speed modifications are working as expected.
