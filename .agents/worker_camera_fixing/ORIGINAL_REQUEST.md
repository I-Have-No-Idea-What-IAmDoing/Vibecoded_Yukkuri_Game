## 2026-06-21T23:28:19Z

Objective:
Apply robust bugfixes to the camera controller implementations in `src/camera/mod.rs` (Rust) and `src/yukkuri_game/engine/camera.py` (Python), and update the stress tests to verify the corrected, safe behavior.

Detailed Fix Requirements:
1. **Low Frame Rate Lerp Instability / Overshoot**:
   - In both `src/camera/mod.rs` (`camera_follow_system` and `camera_zoom_system`) and `src/yukkuri_game/engine/camera.py` (follow and zoom updates), clamp the lerp factor to `1.0`. E.g., `let lerp_factor = (controller.lerp_speed * dt).min(1.0);` and `let zoom_factor = (controller.zoom_speed * dt).min(1.0);`.
   - Ensure the final zoom/scale value is also clamped between `min_zoom` and `max_zoom` so it never becomes negative or exceeds bounds. E.g., `orthographic.scale = orthographic.scale.clamp(controller.min_zoom, controller.max_zoom);`.
2. **Infinite Panning**:
   - In `camera_pan_system` (Rust) and the Python panning code, clamp the camera's translation/position coordinates to `[0.0, world_width]` and `[0.0, world_height]`.
3. **Negative Config Crash**:
   - In `src/camera/mod.rs`, ensure clamping ranges are safe even if width/height are negative. Use `0.0` as the minimum and `width.max(0.0)` as the maximum. E.g. `camera_transform.translation.x.clamp(0.0, width.max(0.0))`.
4. **NaN Coordinate Protection**:
   - In `camera_follow_system`, verify target transform coordinates are finite: `target_transform.translation.x.is_finite() && target_transform.translation.y.is_finite()`. If not, do NOT follow or update translation to NaN.
5. **Tracking Cleanup on Despawn**:
   - In `camera_follow_system`, if the tracked entity is missing (i.e. `target_query.get(tracked)` is `Err`), set `controller.tracked_entity = None` to clear tracking.
6. **Mouse Motion Event Accumulation**:
   - In `camera_pan_system` (Rust), read/drain `mouse_motion` events unconditionally every frame. Only apply the computed drag delta if middle-click is pressed.
7. **Query Constraints**:
   - Remove `With<Collider>` from the `camera_follow_system` query target signature so any entity with a `Transform` can be followed.
8. **Update Tests**:
   - Update `tests/rendering_camera_test.rs` and `tests/systems/test_camera.py` to assert the correct, fixed behavior instead of the buggy behaviors.
   - For example:
     - Assert that panning stays clamped.
     - Assert that large dt doesn't overshoot position or scale.
     - Assert that negative world settings do not panic (assert that it handles it safely).
     - Assert that NaN coordinates do not corrupt the camera translation.
     - Add a new test `test_camera_update_clears_tracking_on_missing_entity` which spawns a target, tracks it, despawns it, updates, and asserts `tracked_entity` becomes `None`.

Completion Criteria:
- All 10 Rust integration tests (`cargo test`) pass.
- All Python camera tests pass.
- The codebase compiles clean without errors or warnings.
- Handoff report written to `c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_camera_fixing\handoff.md`.
