# Implementation Tasks: Robust AI Rewrite

## Phase 1: Core Components & Systems (Motor Layer)

- [ ] **Define New Components**
    - [ ] Create `ActionCommand` component (generic or specific subclasses like `MoveCommand`, `InteractCommand`).
    - [ ] Create `Path` component (to store the list of waypoints, separate from `AIState`).
    - [ ] Create `Goal` component (to store the current high-level objective).

- [ ] **Implement SteeringSystem**
    - [ ] Create `src/yukkuri_game/game/systems/steering_system.py`.
    - [ ] Implement logic to read `MoveCommand` and `Path`.
    - [ ] Implement path following (steering behaviors: Seek, Arrive).
    - [ ] Implement simple obstacle avoidance (raycasts).
    - [ ] Apply velocity to `PhysicsBody`.

- [ ] **Implement NavigationSystem**
    - [ ] Create `src/yukkuri_game/game/systems/navigation_system.py`.
    - [ ] Logic: logic to check if `MoveCommand` destination > `Path` end.
    - [ ] Request path from `NavigationService` (async).
    - [ ] Update `Path` component when path arrives.
    - [ ] Handle failures (e.g., add `status=FAILED` to `MoveCommand` so AI knows).

## Phase 2: Action Refactoring (Tactical Layer)

- [ ] **Refactor `MoveToTarget` Action**
    - [ ] Remove all direct velocity code, pathfinding requests, and drift logic.
    - [ ] Change `update()` to:
        1. Check if `MoveCommand` exists. If not, add it.
        2. Monitor `MoveCommand` status (RUNNING, COMPLETED, FAILED).
        3. Return appropriate `py_trees.Status`.

- [ ] **Refactor `Interact` Action**
    - [ ] Retrieve target.
    - [ ] Add `InteractCommand`.
    - [ ] Wait for `InteractCommand` result or `InteractionSystem` feedback.

## Phase 3: Cognitive Layer Integration

- [ ] **Update `UtilitySelector`**
    - [ ] Ensure it correctly sets/clears `Goal` components.
    - [ ] Allow it to interrupt current actions by removing `ActionCommand` components when switching goals.

- [ ] **Cleanup**
    - [ ] Remove `AIState.path`, `AIState.path_requesting`, etc.
    - [ ] Deprecate old monolithic logic in `behavior.py`.
    - [ ] Verify no regressions in existing behaviors (Eat, Play, Social).
