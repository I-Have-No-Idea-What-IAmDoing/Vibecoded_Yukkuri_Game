# Implementation Plan: Pragmatic Movement Polish

This plan outlines the concrete steps to implement the design described in "Pragmatic Movement Polish". The approach is phased to ensure stability and allow for iterative tuning.

## Phase 1: Foundation (Components & Data)

1.  **[ ] Define `Locomotion` Component**:
    *   Create the new `Locomotion` dataclass in `src/yukkuri_game/game/components.py`.
    *   Fields: `max_speed`, `acceleration`, `hop_enthusiasm`, `is_moving`, `hop_timer`.
    *   *Verification*: Ensure the component can be added to a Yukkuri entity without errors.

2.  **[ ] Update `Renderable` Component**:
    *   Add the `visual_offset: Vector2` field to the existing `Renderable` component in `src/yukkuri_game/game/components.py`.
    *   *Verification*: Confirm that existing rendering code still functions correctly with the added field.

3.  **[ ] Update Entity Factory**:
    *   In the `YukkuriFactory` (or equivalent), add the new `Locomotion` component to all newly created Yukkuris.

## Phase 2: Visuals (Animation System)

4.  **[ ] Create `AnimationSystem`**:
    *   Create a new file: `src/yukkuri_game/game/systems/animation_system.py`.
    *   Implement the system's `process` loop to iterate over entities with `Locomotion`, `Renderable`, and `PhysicsBody` components.
    *   Implement the "hop" logic:
        *   If `Locomotion.is_moving` is true, increment `hop_timer`.
        *   Calculate a `y_offset` based on the `hop_timer` (e.g., `sin(hop_timer * PI * 2) * 10 * hop_enthusiasm`).
        *   Set `Renderable.visual_offset.y = y_offset`.
    *   *Initial Stub*: For now, the system only handles the visual hop. Squash/stretch can be added later.

5.  **[ ] Update `RenderSystem`**:
    *   Modify the `RenderSystem` to read the `Renderable.visual_offset`.
    *   When drawing the sprite, add the offset to its final screen position: `screen_pos = world_pos + visual_offset`.

6.  **[ ] Register `AnimationSystem`**:
    *   Add the new `AnimationSystem` to the main game loop's system list.
    *   **Crucially**, ensure it runs *after* the `PhysicsSystem` to ensure it's using the most up-to-date position data for rendering.

## Phase 3: AI and Physics Refinement

7.  **[ ] Refactor `MoveToTarget` Action**:
    *   Modify the `MoveToTarget` action in `src/yukkuri_game/game/ai/behavior.py`.
    *   When the action starts, it should set `Locomotion.is_moving = True`.
    *   When it ends (success, failure), it must set `Locomotion.is_moving = False` and reset `hop_timer` to `0.0`.
    *   Instead of using a hardcoded speed, its steering calculation should be capped by `Locomotion.max_speed`.
    *   **Decision**: Choose between applying force or setting velocity. For initial implementation, continue setting `body.velocity` as it's simpler and lower risk. A future task can explore using forces for a "weightier" feel.

## Phase 4: Stat Integration and Tuning

8.  **[ ] Create `StatSyncSystem`**:
    *   Create a new file: `src/yukkuri_game/game/systems/stat_sync_system.py`.
    *   Implement the system to run on a slower tick (e.g., once per second).
    *   Add logic to update `Locomotion.max_speed` and `Locomotion.hop_enthusiasm` based on `YukkuriStats` (energy, age, etc.).
    *   Register the system in the main game loop.

9.  **[ ] Tuning and Polish**:
    *   Playtest the game and tweak the default values in the `Locomotion` component.
    *   Adjust the formula in `AnimationSystem` for the hop height and timing.
    *   Adjust the formulas in `StatSyncSystem` to create noticeable but balanced effects.
    *   Once the core loop is stable, add squash-and-stretch logic to the `AnimationSystem`.

This phased approach ensures that a playable game is maintained at every step, minimizes risk, and provides clear, verifiable outcomes for each task.