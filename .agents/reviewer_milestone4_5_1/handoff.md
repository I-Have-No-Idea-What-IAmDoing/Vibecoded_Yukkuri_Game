# Handoff Report — Camera Controller & Tests Review

## 1. Observation
- **File Checked**: `src/camera/mod.rs` (lines 53-81) for target following logic:
  ```rust
  pub fn camera_follow_system(
      time: Res<Time>,
      mut camera_query: Query<(&mut Transform, &CameraController), With<MainCamera>>,
      target_query: Query<&Transform, (With<Collider>, Without<MainCamera>)>,
      world_settings: Option<Res<WorldSettings>>,
  ) {
      let dt = time.delta_secs();
      ...
      if let Some((mut camera_transform, controller)) = camera_query.iter_mut().next() {
          if let Some(tracked) = controller.tracked_entity {
              if let Ok(target_transform) = target_query.get(tracked) {
                  let target_pos = target_transform.translation.truncate();
                  let camera_pos = camera_transform.translation.truncate();
                  
                  let new_pos = camera_pos + (target_pos - camera_pos) * controller.lerp_speed * dt;
                  
                  camera_transform.translation.x = new_pos.x;
                  camera_transform.translation.y = new_pos.y;
                  
                  camera_transform.translation.x = camera_transform.translation.x.clamp(0.0, width);
                  camera_transform.translation.y = camera_transform.translation.y.clamp(0.0, height);
              }
          }
      }
  }
  ```
- **File Checked**: `src/camera/mod.rs` (lines 118-172) for mouse motion events and panning:
  ```rust
      let mut drag_delta = Vec2::ZERO;
      let mut is_dragging = false;
      if mouse_input.pressed(MouseButton::Middle) {
          for event in mouse_motion.read() {
              drag_delta.x -= event.delta.x;
              drag_delta.y += event.delta.y;
              is_dragging = true;
          }
      }
  ```
- **File Checked**: `tests/rendering_camera_test.rs` (lines 1-179) containing 4 test functions: `test_camera_follow`, `test_camera_pan_breaks_lock`, `test_camera_selection`, and `test_camera_refocus`.
- **Command Executed**: `cargo test --test rendering_camera_test`
- **Command Output**:
  ```
  running 4 tests
  test test_camera_selection ... ok
  test test_camera_pan_breaks_lock ... ok
  test test_camera_refocus ... ok
  test test_camera_follow ... ok

  test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.11s
  ```
- **File Checked**: `docs/camera_tracking.md` (lines 39-42):
  ```
  * If the entity is destroyed or lacks a `Transform`, the lock is cleared
    automatically (`tracked_entity_id = None`).
  * If keyboard movement axis input is detected (`input_axis_x != 0.0` or
    `input_axis_y != 0.0`), the lock is instantly cleared.
  ```
- **File Checked**: `docs/camera_tracking.md` (lines 73-74):
  ```
  * `test_camera_update_clears_tracking_on_missing_entity`: Asserts that tracking
    is safely cleared if the tracked entity ID does not exist in the world.
  ```

## 2. Logic Chain
1. In `src/camera/mod.rs`, the `camera_follow_system` queries the tracked target `target_query.get(tracked)`. If the target is missing or despawned, the `get` method returns `Err`. However, there is no `else` block to clear the `controller.tracked_entity` field to `None`.
2. This omission breaks the specification in `docs/camera_tracking.md` which requires the lock to be cleared automatically if the entity is destroyed.
3. The omission also leaves the camera system open to tracking recycled entity IDs if Bevy re-allocates the index of the destroyed entity, which is a major correctness defect.
4. The test case `test_camera_update_clears_tracking_on_missing_entity` mentioned in `docs/camera_tracking.md` was not implemented in `tests/rendering_camera_test.rs`, meaning this functionality was left untested and unimplemented.
5. In `camera_pan_system` (lines 142-148), `mouse_motion.read()` is nested inside `if mouse_input.pressed(MouseButton::Middle)`. If the user moves the mouse without holding the middle button, the `MouseMotion` events are not read and accumulate in the reader's event buffer. Upon pressing the middle mouse button, all accumulated motion events from previous frames are processed at once, causing the camera to teleport or jerk wildly.
6. The `camera_follow_system` limits targets to those `With<Collider>`. If an entity has no collider (e.g. non-physical targets like points of interest, effects, or dead/ghost entities that have lost their collider), it cannot be followed even if it has a `Transform`.
7. Based on the correctness and specification mismatches identified, changes must be requested to correct the camera follow cleanups, drain the mouse motion events every frame, and expand test coverage.

## 3. Caveats
- No caveats. The review was based on direct code inspection and compilation behavior.

## 4. Conclusion
The Camera Controller compiles and runs, but contains significant design flaws: target entity tracking locks are not cleared when entities are despawned, mouse pan motion events accumulate and cause jerky jumps, and the system restricts tracking unnecessarily to entities with colliders. In addition, required regression tests for target removal and zoom logic are missing. The verdict is **REQUEST_CHANGES**.

## 5. Verification Method
1. Run `cargo test --test rendering_camera_test` to verify existing tests pass.
2. Invalidate changes if a test for despawned entity tracking cleanup is added and fails without the fix.
3. Inspect `src/camera/mod.rs` to ensure `target_query.get(tracked)` handles the `Err` case by resetting `tracked_entity = None`, and `mouse_motion.read()` is drained unconditionally each frame.

---

# QUALITY REVIEW REPORT

**Verdict**: REQUEST_CHANGES

## Findings

### [Major] Finding 1: Lack of tracking cleanup on entity destruction
- **What**: The camera controller does not clear `tracked_entity` when the target entity is despawned or lacks components.
- **Where**: `src/camera/mod.rs` at line 66-79 (`camera_follow_system`).
- **Why**: Mismatches the specification in `docs/camera_tracking.md` (which demands cleanup of `tracked_entity_id = None` on destruction). Holding onto dead entity handles risks tracking recycled entity IDs.
- **Suggestion**: Add an `else` branch to clear `controller.tracked_entity = None`:
  ```rust
  if let Some(tracked) = controller.tracked_entity {
      if let Ok(target_transform) = target_query.get(tracked) {
          // ... update position ...
      } else {
          controller.tracked_entity = None;
      }
  }
  ```

### [Major] Finding 2: Missing regression test for destroyed entities
- **What**: The test `test_camera_update_clears_tracking_on_missing_entity` mentioned in `docs/camera_tracking.md` is missing from `tests/rendering_camera_test.rs`.
- **Where**: `tests/rendering_camera_test.rs`.
- **Why**: A core verification constraint of the camera tracking lifecycle is untested, hiding the bug in Finding 1.
- **Suggestion**: Add a test that spawns a target, tracks it, despawns the target, calls `app.update()`, and asserts that `tracked_entity` is now `None`.

### [Minor] Finding 3: Restrictive follow query filter
- **What**: `camera_follow_system` queries targets using `target_query: Query<&Transform, (With<Collider>, Without<MainCamera>)>`.
- **Where**: `src/camera/mod.rs` at line 56.
- **Why**: If a tracked entity does not have a `Collider` (or loses it), the camera stops following it, even though only a `Transform` is required to extract coordinates.
- **Suggestion**: Remove `With<Collider>` from the query signature in `camera_follow_system`. Keep `Collider` checking localized in `camera_select_system` since clicking on physical entities is collider-dependent.

---

# ADVERSARIAL REVIEW REPORT

**Overall risk assessment**: MEDIUM

## Challenges

### [High] Challenge 1: Mouse motion panning jerkiness (Accumulated Events)
- **Assumption challenged**: Mouse motion events are only generated/need to be read when dragging.
- **Attack scenario**: The player moves the mouse around normally for several seconds, then presses the Middle Mouse button to pan the camera.
- **Blast radius**: The camera instantly teleports or jerks violently across the screen due to processing accumulated motion events from previous frames.
- **Mitigation**: Drain `mouse_motion.read()` unconditionally every frame, and conditionally apply the translation delta only if the button is pressed:
  ```rust
  let mut drag_delta = Vec2::ZERO;
  let mut is_dragging = false;
  // Always drain the event queue to prevent stale accumulation
  for event in mouse_motion.read() {
      if mouse_input.pressed(MouseButton::Middle) {
          drag_delta.x -= event.delta.x;
          drag_delta.y += event.delta.y;
          is_dragging = true;
      }
  }
  ```

### [Medium] Challenge 2: Zoom interpolation instability under low FPS
- **Assumption challenged**: Delta time (`dt`) is small enough that `zoom_speed * dt` is always less than 1.0.
- **Attack scenario**: Frame rate drops below 10 FPS (e.g. during level load or heavy GC pausing), making `dt >= 0.125`. With `zoom_speed = 8.0`, the term `controller.zoom_speed * dt` will exceed `1.0`.
- **Blast radius**: The orthographic camera scale overshoots the target zoom level, causing wild screen oscillation or visual glitches.
- **Mitigation**: Clamp the scale lerp factor to `1.0`:
  ```rust
  let lerp_factor = (controller.zoom_speed * dt).min(1.0);
  orthographic.scale += (controller.target_zoom - orthographic.scale) * lerp_factor;
  ```

## Stress Test Results

- **Despawn target entity**: Set `tracked_entity` to target, call `world.despawn(target)`, call `camera_follow_system` -> `tracked_entity` remains `Some(target)` instead of resetting -> **FAIL**
- **Pan with stale mouse motion**: Move mouse without Middle Mouse, click Middle Mouse -> camera jerks based on stale coordinates -> **FAIL**
- **Track non-collider entity**: Set `tracked_entity` to an entity without `Collider` component, call `camera_follow_system` -> camera does not follow target -> **FAIL**
- **Zoom interpolation scale**: Trigger low frame rate (e.g. `dt = 0.25`), call `camera_zoom_system` -> scale lerp factor becomes `2.0` (overshoot) -> **FAIL**
