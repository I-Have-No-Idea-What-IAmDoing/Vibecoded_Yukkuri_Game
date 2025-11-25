# Actionable Tasks for Movement System Refactoring

This document outlines the step-by-step tasks required to implement the `MovementController` as described in `design.md`. The goal is to replace the distributed movement systems with a single, stateful component.

## Phase 1: Core `MovementController` Implementation

1.  [ ] **Define Base `MovementController` Component**
    -   Create a new file for the component, e.g., `src/yukkuri_game/game/components/movement_controller.py`.
    -   Implement the `MovementController` class with a stateful design, including properties like `is_moving` and `path`.
    -   Define the public methods `move_to(target_position)` and `stop()`.
    -   *Verification*: The component can be created and attached to an entity.

2.  [ ] **Integrate Pathfinding**
    -   The `MovementController`'s `__init__` should accept a reference to the existing `Pathfinder` service.
    -   The `move_to` method should use the pathfinder to calculate a path and store it. It should handle both success and failure cases (e.g., no path found).

3.  [ ] **Implement Core `update` Logic**
    -   Add an `update(dt)` method to the `MovementController`.
    -   Inside `update`, implement the core logic for path following:
        -   Check if the entity has reached the current waypoint.
        -   Advance to the next waypoint.
        -   Calculate a steering force (e.g., "seek") towards the current waypoint.
        -   Apply the force to the entity's physics body.
        -   Set `is_moving` to `False` upon reaching the final destination.
    -   Implement basic "stuck" detection (e.g., a simple timer).

4.  [ ] **Create `MovementSystem`**
    -   Create a new, simple system (`src/yukkuri_game/game/systems/movement_system.py`).
    -   This system's only job is to iterate through all entities with a `MovementController` component and call their `update(dt)` method each frame.
    -   Register this system to run in the main game loop, likely before the physics step.

## Phase 2: AI & Entity Integration

5.  [ ] **Refactor `MoveToTarget` Behavior Tree Action**
    -   Modify `src/yukkuri_game/game/ai/behavior.py`.
    -   On the first tick, get the `MovementController` from the entity and call `controller.move_to(target)`.
    -   On subsequent ticks, check `controller.is_moving` to determine whether to return `RUNNING`, `SUCCESS`, or `FAILURE`.
    -   Remove all old pathfinding and steering logic from the action.

6.  [ ] **Update Entity Factory**
    -   Modify the `YukkuriFactory` to attach the new `MovementController` component to all Yukkuri entities upon creation.

7.  [ ] **Refactor Other AI Actions**
    -   Update other movement-related actions (e.g., `Wander`, `Flee`) to use the `MovementController`.
    -   Ensure actions that need to interrupt movement (e.g., `Interact`) can call `controller.stop()` correctly.

## Phase 3: Character-Specific Movement

8.  [ ] **Create `YukkuriMovementController`**
    -   In a relevant file, create a `YukkuriMovementController` that inherits from the base `MovementController`.
    -   Update the `YukkuriFactory` to attach this specific controller instead of the base one.

9.  [ ] **Implement Yukkuri-Specific Logic**
    -   Override the `update(dt)` method in `YukkuriMovementController`.
    -   Add character-specific logic for "waddling" and "stumbling," as conceptualized in the design document.
    -   Ensure the new logic calls `super().update(dt)` to retain the base path-following behavior.

## Phase 4: Cleanup & Verification

10. [ ] **Remove Deprecated Code**
    -   Delete the old movement-related components: `MovementRequest`, `Path`, and `SteeringAgent`.
    -   Delete the old movement-related systems: `NavigationSystem` and `SteeringSystem`.
    -   Clean up any unused utility functions related to the old approach.

11. [ ] **Testing**
    -   Run all existing tests to check for regressions.
    -   Create new unit tests for the `MovementController` to verify its state logic and pathfinding requests.
    -   Perform extensive playtesting to ensure movement is robust, bug-free, and feels more characterful.
