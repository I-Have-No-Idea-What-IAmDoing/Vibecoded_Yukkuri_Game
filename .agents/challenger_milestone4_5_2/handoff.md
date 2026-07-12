# Camera Controller Empirical Verification Report

## 1. Observation
### Python Camera Controller (`src/yukkuri_game/engine/camera.py`)
- **Lerp Equation**:
  ```python
  self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt
  ```
  and
  ```python
  self.camera_x += (trans.x - self.camera_x) * 5.0 * dt
  self.camera_y += (trans.y - self.camera_y) * 5.0 * dt
  ```
- **Screen-to-World Translation**:
  ```python
  wx = (sx - screen_w / 2) / (self.zoom * self.correction_x) + self.camera_x
  wy = (sy - screen_h / 2) / (self.zoom * self.correction_y) + self.camera_y
  ```
- **Panning Logic**:
  ```python
  def pan(self, dx: int, dy: int) -> None:
      self.tracked_entity_id = None
      self.camera_x -= dx / self.zoom
      self.camera_y -= dy / self.zoom
  ```

### Rust/Bevy Camera Controller (`src/camera/mod.rs`)
- **Zoom Scale Equation**:
  ```rust
  if let Projection::Orthographic(ref mut orthographic) = *projection {
      orthographic.scale += (controller.target_zoom - orthographic.scale) * controller.zoom_speed * dt;
  }
  ```
- **Panning Logic**:
  ```rust
  if final_translation != Vec2::ZERO {
      transform.translation += final_translation.extend(0.0);
      controller.tracked_entity = None;
  }
  ```

---

## 2. Logic Chain
1. **Numerical Instability of Euler Lerp**:
   - The integration equation $V_{new} = V_{current} + (V_{target} - V_{current}) \times k \times dt$ is mathematically equivalent to:
     $$V_{new} = V_{current} (1 - k \cdot dt) + V_{target} (k \cdot dt)$$
   - If $|1 - k \cdot dt| > 1.0$ (i.e., $k \cdot dt > 2.0$), the system is unstable and the value diverges.
   - If $1.0 < k \cdot dt < 2.0$, the value overshoots and oscillates around the target.
   - In Python, $k = 5.0$. Hence, zoom and follow translation diverge for $dt > 0.4$ seconds, and overshoot for $dt > 0.2$ seconds.
   - In Rust, $k = 8.0$. Hence, projection scale diverges for $dt > 0.25$ seconds, and overshoots for $dt > 0.125$ seconds. Because Bevy clamps maximum real delta time to 0.25 seconds by default, it oscillates infinitely at exactly $dt = 0.25$s (e.g. toggling between scale `1.0` and `-0.5` on consecutive ticks).

2. **Negative and Zero Zoom Scale Vulnerabilities**:
   - Neither system clamps the actual zoom/projection scale during the interpolation steps (they only clamp the `target_zoom`).
   - If $k \cdot dt > 1.0$, the interpolation can overshoot beyond the `target_zoom` bounds. If `target_zoom` is set to the minimum limit (e.g. 0.5 in Python, 0.25 in Rust), an overshoot can drive the actual zoom below the minimum limit and even below 0.0.
   - If `zoom` is exactly 0.0, the Python `screen_to_world` formula performs a division by zero, throwing a `ZeroDivisionError` and crashing the engine.
   - If `zoom` is negative, the coordinate space flips, resulting in reversed panning controls and mirrored/flipped rendering coordinates. In Pygame, negative scaling factors result in silent failures during rendering passes (returning `None` in `SurfaceCache._create_surface` instead of rendering the sprite).

3. **Infinite Panning Boundary Vulnerability**:
   - Neither the Python `pan` nor the Rust `camera_pan_system` contains checks to clamp the final camera position to the world boundaries (defined in `WorldSettings`).
   - Consequently, manual keyboard or middle-mouse drag panning allows moving the camera infinitely outside the world coordinates.

---

## 3. Caveats
- Real-time display rendering and GPU/OpenGL shader behavior under negative/zero zoom was not visually tested because tests are run in headless environment mode (`testing/driver.py` and cargo unit tests).
- Bevy's default time step maximum clamp prevents extreme time steps (e.g., several seconds long) from causing infinite divergence in normal circumstances, but does not prevent infinite oscillation at the clamping threshold ($dt = 0.25$s) or overshoot.

---

## 4. Conclusion
- Both Python and Rust Camera controller implementations suffer from:
  1. **Numerical instability** under high delta times (frame drops), allowing zoom and translation coordinates to overshoot and/or diverge.
  2. **Zoom boundary violations** where the actual zoom/scale can become negative or zero due to unchecked interpolation overshoots.
  3. **Engine crashes** (in Python, `ZeroDivisionError` in `screen_to_world` when `zoom` reaches 0.0).
  4. **Boundary escape** where manual camera panning allows moving the camera outside the game world limits.
- **Recommended Mitigations**:
  1. Replace the Euler integration lerp with a time-independent framing rate correction formula (e.g., $V_{new} = V_{target} + (V_{current} - V_{target}) \times e^{-k \cdot dt}$ or a clamp on $k \cdot dt$ to maximum 1.0).
  2. Explicitly clamp `self.zoom` / `orthographic.scale` to `(min_zoom, max_zoom)` after every interpolation step.
  3. Clamp camera positions `camera_x` and `camera_y` to world boundaries in the panning systems.

---

## 5. Verification Method
### Python Tests
Execute the Python test suite to verify the camera stress and zoom stability tests:
```bash
uv run pytest tests/systems/test_camera.py
```
- Inspect tests under `TestCameraStress` and `TestCameraZoomStability` in `tests/systems/test_camera.py`.
- They verify that zoom/translation overshoot occurs under large $dt$ and that a zoom of `0.0` raises a `ZeroDivisionError`.

### Rust/Bevy Tests
Execute the cargo integration tests for the camera plugin:
```bash
cargo test --test rendering_camera_test
```
- Inspect tests `test_camera_overshoot_large_dt`, `test_camera_negative_zoom_scale`, and `test_camera_pan_beyond_boundaries` in `tests/rendering_camera_test.rs`.
- These tests assert and confirm that overshoot, negative zoom scaling, and boundary escapes occur in the Bevy controller systems under stress scenarios.
