# Actionable Tasks for Movement System Overhaul

This document outlines the step-by-step plan to implement the Movement System overhaul described in [design.md](./design.md).

## Phase 1: Core Infrastructure (Components & Systems)

The goal of this phase is to set up the ECS structures without breaking the existing game.

- [ ] **Create Components**:
    - `src/yukkuri_game/game/components.py` (or new `movement_components.py`):
        - Define `MovementTarget` (dataclass: target_pos, path, tolerance).
        - Define `SteeringAgent` (dataclass: max_speed, max_force, weights).
        - Define `LocomotionState` (dataclass: gait_type, timers).
- [ ] **Create Systems Skeletons**:
    - `src/yukkuri_game/game/systems/movement_system.py`:
        - Create `NavigationSystem` class (placeholder).
        - Create `SteeringSystem` class (placeholder).
        - Create `LocomotionSystem` class (placeholder).
- [ ] **Register Systems**:
    - Update `src/yukkuri_game/game/game_manager.py` (or `core.py`) to register these new systems (initially inactive or operating on empty sets).

## Phase 2: Navigation & Pathfinding Migration

Extract pathfinding logic from `MoveToTarget` into the `NavigationSystem`.

- [ ] **Implement `NavigationSystem`**:
    - Watch for entities with `MovementTarget` that have a valid `target_pos` but empty `path`.
    - Call `NavigationService.find_path`.
    - Store result in `MovementTarget.path`.
    - Handle "no path found" scenarios (set error flag on component).
- [ ] **Unit Test**: Verify `NavigationSystem` correctly populates paths given a start and end point.

## Phase 3: Steering Behaviors

Implement the math for steering forces.

- [ ] **Implement `SteeringSystem`**:
    - **Path Following**: Calculate `Seek` force to the next waypoint in `MovementTarget.path`. Handle waypoint switching when close enough.
    - **Separation**: Query `PhysicsSystem` or `World` for nearby `SteeringAgent` entities. Calculate separation force.
    - **Force Integration**: Sum forces, clamp to `max_force` and `max_speed`.
    - **Output**: For now, apply directly to `PhysicsBody.velocity` (transitional step) or store in a temp variable.
- [ ] **Debug Rendering**: Add debug lines in `SteeringSystem` (if possible via global debug flag) to visualize force vectors.

## Phase 4: Locomotion & Physics Integration

Switch from direct velocity control to force-based movement.

- [ ] **Implement `LocomotionSystem`**:
    - Read the desired velocity/force from `SteeringSystem`.
    - Apply forces/impulses to `PhysicsBody` using Pymunk API (`apply_force`, `apply_impulse`).
    - Implement "Hopping" gait: Only apply force periodically (e.g., every 0.5s) to simulate Yukkuri hopping.
- [ ] **Refine Physics**: Tune friction/damping in `PhysicsSystem` to prevent sliding forever.

## Phase 5: Behavior Tree Integration (The Switch)

Replace the old logic with the new ECS-driven approach.

- [ ] **Refactor `MoveToTarget` Action**:
    - **Initialise**: Add `MovementTarget` and `SteeringAgent` components to the entity. Set `target_pos`.
    - **Update**: Monitor `MovementTarget`.
        - If `dist < tolerance`: Return `SUCCESS`.
        - If stuck/no path: Return `FAILURE`.
        - Else: Return `RUNNING`.
    - **Terminate**: Remove `MovementTarget` component.
- [ ] **Refactor `Wander` Action**:
    - Generate random point.
    - Use the new `MoveToTarget` logic (or set components directly).
- [ ] **Cleanup**: Remove old pathfinding/movement code from `behavior.py`.

## Phase 6: Tuning & Polish

- [ ] **Tune Steering Weights**: Adjust Seek vs Separation weights to get nice group behavior.
- [ ] **Tune Locomotion**: Adjust hop impulse strength and frequency for different Yukkuri types (e.g., babies hop faster/smaller).
- [ ] **Stress Test**: Spawn 50+ Yukkuris and ensure performance remains stable and they don't merge into a singularity.
