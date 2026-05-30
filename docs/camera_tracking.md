# Camera Tracking and Entity Following

The game camera supports a smooth, priority-aware entity tracking system that
allows players to automatically follow a selected Yukkuri or item as it moves
through the world.

---

## 🎮 Player Controls

The tracking system is designed to be fully seamless and intuitive:

| Action | Control | Behavior |
| :--- | :--- | :--- |
| **Select and Follow** | Left-Click (on entity) | Selects the entity and automatically engages camera follow lock. |
| **Manual Break-Lock** | WASD / Arrow Keys | Manual camera keyboard movement instantly unlocks the camera. |
| **Drag Break-Lock** | Middle-Mouse Drag | Drag-panning the camera instantly unlocks the camera. |
| **Re-focus / Follow** | `F` Key | Instantly re-locks and centers the camera on the currently selected entity. |

---

## 🛠️ Architecture & Data Flow

The tracking system is implemented across three coordinated layers of the
engine: the Camera service, ECS Selection Commands, and the Input System.

### 1. The Camera Service (`engine/camera.py`)
The `Camera` class maintains a `tracked_entity_id` field:
* In `Camera.update(dt, world)`:
  * If `tracked_entity_id` is set, it queries the ECS World for that entity's
    `Transform` component.
  * If the entity exists, the camera's `camera_x` and `camera_y` are smoothly
    interpolated toward the entity's position using a time-scaled linear
    interpolation (lerp):
    ```python
    self.camera_x += (trans.x - self.camera_x) * 5.0 * dt
    self.camera_y += (trans.y - self.camera_y) * 5.0 * dt
    ```
  * If the entity is destroyed or lacks a `Transform`, the lock is cleared
    automatically (`tracked_entity_id = None`).
  * If keyboard movement axis input is detected (`input_axis_x != 0.0` or
    `input_axis_y != 0.0`), the lock is instantly cleared.
* In `Camera.pan(dx, dy)`:
  * Panning the camera via middle-mouse drag immediately clears the tracking
    lock (`tracked_entity_id = None`).

### 2. Selection Commands (`game/commands.py`)
* **`SelectEntitiesCommand`**:
  * Triggered on left-click or drag-release.
  * If exactly **one** entity is selected, it updates the camera's
    `tracked_entity_id` to that entity's ID, instantly centering and following.
  * If multiple or zero entities are selected, it clears the tracking lock.
* **`FollowSelectedCommand`**:
  * Enqueued when the player presses the `F` key.
  * Locates the single selected entity in the world and re-assigns its ID to
    `camera.tracked_entity_id`, re-focusing and tracking.

### 3. Input System (`game/input_system.py`)
* The gameplay input context maps `"follow"` to `pygame.K_f` inside the
  `InputManager`.
* The `InputSystem` checks for `is_action_just_pressed("follow")` and emits a
  `FollowSelectedCommand` to the processor.

---

## 🧪 Automated Testing

The tracking behavior is fully verified by headless unit tests inside
`tests/systems/test_camera.py` under the `TestCameraFollowing` class:

* `test_camera_update_centers_on_tracked_entity`: Asserts that camera update
  smoothly interpolates coordinates closer to the target position.
* `test_camera_update_clears_tracking_on_missing_entity`: Asserts that tracking
  is safely cleared if the tracked entity ID does not exist in the world.
* `test_camera_input_clears_tracking`: Asserts that keyboard WASD camera pan
  instantly releases the follow lock.
* `test_camera_pan_clears_tracking`: Asserts that middle-mouse panning
  instantly releases the follow lock.
