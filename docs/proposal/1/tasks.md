# Actionable Tasks for Movement System Overhaul

This document outlines the step-by-step tasks required to implement the Yukkuri Movement System Overhaul described in `design.md`.

## Phase 1: Preparation & Component Definition

1.  [ ] **Create New Components**
    -   Define `MovementRequest` in `src/yukkuri_game/game/components.py`.
    -   Define `Path` in `src/yukkuri_game/game/components.py`.
    -   Define `SteeringAgent` in `src/yukkuri_game/game/components.py`.
    -   *Verification*: Verify components are importable and have correct data fields.

2.  [ ] **Update Entity Factory**
    -   Update `YukkuriFactory` (or equivalent) to attach `SteeringAgent` to new Yukkuris.
    -   Initialize `MovementRequest` and `Path` components on creation (or ensure they can be added dynamically).

## Phase 2: System Implementation

3.  [ ] **Create `NavigationSystem`**
    -   Create `src/yukkuri_game/game/systems/navigation_system.py`.
    -   Implement logic to query `MovementRequest` and update `Path`.
    -   Integrate existing `NavigationService` for A* pathfinding.
    -   Handle dynamic target updates (following a moving entity).

4.  [ ] **Create `SteeringSystem`**
    -   Create `src/yukkuri_game/game/systems/steering_system.py`.
    -   Port steering logic (Seek, Arrive, Wander) from `src/yukkuri_game/game/ai/steering.py` (or keep it as a utility library used by the system).
    -   Implement path following logic (switching waypoints).
    -   Implement stuck detection and local avoidance (raycasting).
    -   Apply velocity to `PhysicsBody` (or `Transform` fallback).

5.  [ ] **Register Systems**
    -   Add `NavigationSystem` and `SteeringSystem` to the World in `src/yukkuri_game/main.py` (or `game_manager.py`).
    -   Ensure correct update order: `AI` -> `Navigation` -> `Steering` -> `Physics`.

## Phase 3: AI Integration

6.  [ ] **Refactor `MoveToTarget` Action**
    -   Modify `src/yukkuri_game/game/ai/behavior.py`.
    -   Strip out pathfinding and direct movement code.
    -   Update `update()` to set `MovementRequest` and return status based on `Path` component.

7.  [ ] **Refactor `Wander` Action**
    -   Update `Wander` to set a random target in `MovementRequest` instead of manually setting blackboard variables.

8.  [ ] **Refactor `Interact` & Social Actions**
    -   Ensure these actions play nicely with the new movement components (e.g., stopping when in range).

## Phase 4: Cleanup & Verification

9.  [ ] **Remove Deprecated Code**
    -   Remove old movement logic from `behavior.py`.
    -   Clean up `NavigationService` if some methods are no longer needed directly by AI.

10. [ ] **Testing**
    -   Run existing tests to ensure no regressions.
    -   Create new test cases for `NavigationSystem` and `SteeringSystem`.
    -   Playtest to verify movement feels smooth and entities don't get stuck.
