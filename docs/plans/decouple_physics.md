# Decouple Physics Step

## Goal
Fix the potential issue where variable `dt` scaling (Time Scale) causes physics instability or "spiral of death".

## Steps

1.  **Update `PhysicsSystem.update`**
    -   **File**: `src/yukkuri_game/game/systems/physics.py`
    -   Current logic: Accumulates `dt`. Steps `time_step` (1/60) until accumulator is drained.
    -   **Issue**: If `dt` (scaled by time_scale 5x) is huge (e.g. 0.1s), we run `step` 6 times. This is generally okay, but if `dt` is *too* large (lag spike + high time scale), it freezes.
    -   **Fix**:
        -   Clamp the input `dt` to a maximum (e.g., 0.25s).
        -   If `dt` > max, we lose time (slow motion) but avoid spiral of death.

2.  **Handle Time Scale**
    -   The `dt` passed to `PhysicsSystem.update` is already scaled by `GameManager.time_scale` in `GameLoop` (presumably).
    -   Verify where `dt` comes from.
    -   If `dt` is raw real time, we need to multiply by `time_scale` inside `PhysicsSystem` or pass scaled `dt`.
    -   *Check*: `GameLoop` likely passes `dt * time_scale`.

3.  **Verification**
    -   **Manual**: Set Time Scale to 10x.
    -   Observe FPS and Physics stability.
    -   Ensure objects don't tunnel through walls.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
