# Handoff Report — Challenger 1 (Camera Controller Review)

This report details the findings from stress-testing and boundary verification of the Camera Controller in `src/camera/mod.rs` (Rust/Bevy) and `src/yukkuri_game/engine/camera.py` (Python).

---

## 1. Observation

### Observed Code Structures and Flaws

#### A. Large Time-Step (Delta Time) Overshoot
In `src/camera/mod.rs`, lines 71-74:
```rust
                let new_pos = camera_pos + (target_pos - camera_pos) * controller.lerp_speed * dt;
                
                camera_transform.translation.x = new_pos.x;
                camera_transform.translation.y = new_pos.y;
```
If `controller.lerp_speed * dt > 1.0`, the term `(target_pos - camera_pos) * (lerp_speed * dt)` scales the difference beyond the actual distance, causing the camera to overshoot the target.

In `src/yukkuri_game/engine/camera.py`, lines 223-224:
```python
                self.camera_x += (trans.x - self.camera_x) * 5.0 * dt
                self.camera_y += (trans.y - self.camera_y) * 5.0 * dt
```
A high `dt` (e.g., `0.5`s) makes the update factor `5.0 * 0.5 = 2.5 > 1.0`, which causes the camera position to overshoot its target by a factor of 2.5.

#### B. Negative Projection Scale / Negative Zoom
In `src/camera/mod.rs`, lines 112-114:
```rust
        if let Projection::Orthographic(ref mut orthographic) = *projection {
            orthographic.scale += (controller.target_zoom - orthographic.scale) * controller.zoom_speed * dt;
        }
```
If `controller.zoom_speed * dt > 1.0` (e.g., `8.0 * 0.5 = 4.0`), the orthographic scale update overshoots the target. If target zoom is low (e.g., `0.25`) and current scale is `1.0`, the update is `1.0 + (0.25 - 1.0) * 4.0 = -2.0`, producing a negative projection scale which flips or breaks viewport rendering.

In `src/yukkuri_game/engine/camera.py`, line 240:
```python
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt
```
A large `dt` causes the zoom factor to overshoot and go negative, resulting in invalid zoom states (e.g., zoom of `-0.25`).

#### C. Out-of-Bounds Panning
In `src/camera/mod.rs`, lines 167-170:
```rust
        if final_translation != Vec2::ZERO {
            transform.translation += final_translation.extend(0.0);
            controller.tracked_entity = None;
        }
```
There is no clamping applied to the camera translation during panning. The camera can pan arbitrarily far outside the map bounds specified in `WorldSettings`.

In `src/yukkuri_game/engine/camera.py`, lines 293-294:
```python
        self.camera_x -= dx / self.zoom
        self.camera_y -= dy / self.zoom
```
There is no bounds validation or clamping applied to panning in the Python camera class either.

#### D. Crash on Negative World settings (Rust/Bevy)
In `src/camera/mod.rs`, lines 76-77:
```rust
                camera_transform.translation.x = camera_transform.translation.x.clamp(0.0, width);
                camera_transform.translation.y = camera_transform.translation.y.clamp(0.0, height);
```
`f32::clamp` in Rust panics if `min > max`. If `WorldSettings.width` or `WorldSettings.height` is configured with negative values (e.g., `-500.0`), the system panics with `min > max` (since `0.0 > -500.0`), crashing the Bevy engine.

#### E. NaN Value Propagation (Rust/Bevy)
In `src/camera/mod.rs`, if the target entity's position coordinates are `f32::NAN`, the camera translation inherits `NaN` values without any sanity checks. This breaks camera tracking and propagates `NaN` transforms down Bevy's rendering tree.

---

## 2. Logic Chain

1. **Premise 1**: The mathematical implementation of lerping (`val += (target - val) * speed * dt`) is frame-rate dependent and mathematically unstable for large `dt` unless capped at `1.0` or modeled as exponential decay `1.0 - (-speed * dt).exp()`.
2. **Premise 2**: Neither the Rust camera implementation nor the Python camera implementation clamps the interpolation factor to `1.0`.
3. **Deduction 1**: Therefore, during frames with high delta-time (`dt`), the camera position and zoom will overshoot targets. This was empirically proven in:
   - `test_camera_overshoot_large_dt` (Rust: camera overshot target at `100.0` and ended at `125.0` because Bevy clamps `dt` to a max of `0.25`s).
   - `test_camera_overshoot_large_dt` (Python: camera overshot target at `100.0` and ended at `250.0`).
   - `test_camera_negative_zoom_scale` (Rust: orthographic scale overshot and reached `-0.5` due to Bevy clamping `dt` to `0.25`s).
   - `test_camera_zoom_overshoot_large_dt` (Python: zoom level overshot and reached `-0.25`).
4. **Premise 3**: Clamping coordinates in `camera_follow_system` is only executed when `tracked_entity` is active. Panning clears the tracking lock (`tracked_entity = None`). Panning does not clamp coordinates.
5. **Deduction 2**: Thus, users can pan the camera infinitely out-of-bounds, bypassing map restrictions. This was empirically proven in:
   - `test_camera_pan_beyond_boundaries` (Rust: panned to `-100.0` due to `dt` clamp to `0.25`s).
   - `test_camera_pan_beyond_boundaries` (Python: panned to `-1800.0`).
6. **Premise 4**: Rust's standard library `f32::clamp(min, max)` panics if `min > max`.
7. **Deduction 3**: Spawning a tracked entity when `WorldSettings` contains negative boundaries causes the camera follow system to invoke `clamp(0.0, negative_value)`, triggering a panic. This was empirically proven in:
   - `test_camera_panic_on_negative_world_bounds` (Rust: panicked with `"min > max"`).
8. **Premise 5**: Bevy's `Transform` does not prevent assigning `NaN` coordinates, and `f32::clamp` returns the input value if it is `NaN`.
9. **Deduction 4**: Thus, a target at `NaN` causes the camera to permanently lose its position and translate to `NaN`. This was empirically proven in:
   - `test_camera_nan_target_position` (Rust: camera translation coordinates became `NaN`).

---

## 3. Caveats

- Interactive drag gestures and keyboard inputs were simulated programmatically in tests. The tests do not simulate interactive multi-threaded environments or hardware mouse interrupts, but they model the resulting events perfectly.
- Rendering effects of negative projection scale (which flips viewports) were verified mathematically and structurally via tests rather than visual snapshotting, as the test suites run in headless mode.

---

## 4. Conclusion

The Camera Controller in `src/camera/mod.rs` and `src/yukkuri_game/engine/camera.py` has multiple vulnerabilities:
1. **Low Frame Rate Instability**: Large time steps cause severe positional and zoom overshoots, creating rendering glitches (negative projection scale) and visual jitter.
2. **Infinite Panning**: Zero bounds clamping during panning allows players to pan the camera away from the game world indefinitely.
3. **Negative Config Crash**: World bounds config validation is missing, allowing a negative boundary to crash the Bevy engine.
4. **NaN Unsafety**: Lack of float validation on entity transforms leads to camera position corruption via NaN values.

**Recommendation**:
- Replace basic multiplication lerp with exponential decay: `val + (target - val) * (1.0 - (-speed * dt).exp())`, or at least clamp the lerp factor: `(speed * dt).min(1.0)`.
- Apply boundaries clamping to panning and manual movement systems in both Python and Rust.
- Add configuration validation to prevent initialization of negative/invalid `WorldSettings`.
- Validate that the target entity's position is finite (`is_finite()`) before updating camera tracking to prevent NaN propagation.

---

## 5. Verification Method

To verify these issues independently, run the newly added test suites:

### Rust Bevy Tests
Run the camera integration tests:
```bash
cargo test --test rendering_camera_test
```
This runs the 9 tests in `tests/rendering_camera_test.rs`, including:
- `test_camera_overshoot_large_dt`
- `test_camera_negative_zoom_scale`
- `test_camera_pan_beyond_boundaries`
- `test_camera_panic_on_negative_world_bounds`
- `test_camera_nan_target_position`

All 9 tests will compile and pass (meaning the panics and overshoots are successfully reproduced and assertively caught).

### Python Engine Tests
Run pytest:
```bash
uv run pytest tests/systems/test_camera.py
```
This runs the 41 camera tests, including the new:
- `test_camera_overshoot_large_dt`
- `test_camera_zoom_overshoot_large_dt`
- `test_camera_pan_beyond_boundaries`

These tests verify the corresponding mathematical vulnerabilities in the Python camera class.
