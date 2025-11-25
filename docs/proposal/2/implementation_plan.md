# Implementation Plan

## Phase 1: Foundation (Components & Data)
1.  **Create `Locomotion` Component**
    *   Define the data structure in `src/yukkuri_game/game/components.py` (or `yukkuri_components.py` if preferred, but likely generic enough for `components.py` if we want other hopping things).
    *   Fields: `state` (enum), `hop_timer`, `z_height`, `z_velocity`, `grounded` (bool), `target_direction` (Vector2).
2.  **Update `YukkuriStats`**
    *   Ensure `YukkuriStats` has fields relevant to movement calculation (e.g. `energy` is there, maybe add `athletics_score`).

## Phase 2: Logic (Systems)
3.  **Create `MovementSystem`**
    *   Create `src/yukkuri_game/game/systems/movement_system.py`.
    *   Implement the State Machine:
        *   `IDLE`: Wait for `target_direction` > 0. Transition to `PRE_HOP`.
        *   `PRE_HOP`: Wait for delay (squash anim). Apply Impulse. Transition to `AIRBORNE`.
        *   `AIRBORNE`: Update `z` via gravity. Check `z <= 0`. Transition to `LANDING`.
        *   `LANDING`: Apply friction. Wait for recovery. Transition to `IDLE`.
    *   Implement Physics Integration:
        *   Use `pymunk.Body.apply_impulse`.
        *   Manage `pymunk.Space.damping` or body friction dynamically (or apply manual counter-force for friction).
4.  **Integrate with `PhysicsSystem`**
    *   Ensure `PhysicsSystem` doesn't conflict (e.g., if it applies global damping, ensure it works with the hopping rhythm).
    *   The `MovementSystem` might need to run *before* `PhysicsSystem`.

## Phase 3: AI Adaptation
5.  **Refactor `MoveToTarget` Action**
    *   Modify `src/yukkuri_game/game/ai/behavior.py`.
    *   Remove direct `phys.body.velocity` assignment.
    *   Instead, set `Locomotion.target_direction` (normalized vector) and maybe `Locomotion.is_moving = True`.
    *   The `MovementSystem` will read this and decide *when* to hop.

## Phase 4: Polish & Tuning
6.  **Visuals**
    *   Update `RenderSystem` (if exists) or the view layer to render the sprite at `y - z_height`.
    *   Add Shadow sprite at `y`.
7.  **Tuning**
    *   Tune Impulse strength vs Mass.
    *   Tune Gravity and Hop Height.
    *   Tune Recovery times based on stats.

## Actionable Task List

- [ ] **Define `Locomotion` Component**: Add to `yukkuri_components.py`.
- [ ] **Create `MovementSystem` Skeleton**: Setup the class and `update` loop.
- [ ] **Implement Hop Physics**: Write the impulse and Z-axis logic in `MovementSystem`.
- [ ] **Refactor `MoveToTarget`**: Change it to output steering intent to `Locomotion` instead of modifying physics directly.
- [ ] **Register `MovementSystem`**: Add it to `Yukkurrium` game loop.
- [ ] **Test & Tune**: Verify movement feels good and stats affect it.
