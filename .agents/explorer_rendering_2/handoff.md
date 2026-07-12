# Handoff Report: FFI Animation Command Parsing & State Sync Design

## 1. Observation
We observed the following definitions and implementations in the codebase:
- In `src/ai/commands.rs`, the `CommandType` enum includes the `PlayAnimation` variant:
  ```rust
  pub enum CommandType {
      MoveTo,
      Flee,
      Speak,
      PlayAnimation,
      Attack,
      Interact,
      ModifyStat,
  }
  ```
- In `src/yukkuri_game/game/systems/behavior_ffi.py`, the Python `PyCommandType.PLAY_ANIMATION` is mapped to `RustCommandType.PlayAnimation`:
  ```python
  MAP_COMMAND_TYPE: dict[PyCommandType, Any] = {
      ...
      PyCommandType.PLAY_ANIMATION: RustCommandType.PlayAnimation,
  }
  ```
- In `src/yukkuri_game/game/systems/animation.py`, the Python-side `_sync_ai_animation` checks:
  ```python
  target_anim = ai_state.current_action.lower()
  # Flight Overrides
  flight = world.try_get_component(entity, Flight)
  if flight:
      if flight.state == FlightState.SWOOPING:
          target_anim = "swoop"
      elif flight.state in (
          FlightState.FLYING,
          FlightState.TAKEOFF,
          FlightState.HOVERING,
      ):
          target_anim = "fly"
  if (
      target_anim in animator.animations
      and target_anim != animator.current_animation
  ):
      self._switch_animation(animator, target_anim)
  ```
- In `src/yukkuri_game/engine/components.py`, `FlightState` enum variants represent:
  ```python
  class FlightState(Enum):
      GROUNDED = 0
      TAKEOFF = 1
      FLYING = 2
      HOVERING = 3
      LANDING = 4
      SWOOPING = 5
      FALLING = 6
  ```
- In `src/yukkuri_game/engine/data_models.py`, `AnimationDefinition` model has attributes representing animation frames, speeds, looping, and events:
  ```python
  class AnimationDefinition(msgspec.Struct):
      name: str
      frames: list[int]
      frame_duration: float
      loop: bool = True
      ping_pong: bool = False
      events: dict[int, str] = msgspec.field(default_factory=dict)
      image: str | None = None
      width: int | None = None
      height: int | None = None
  ```
- Running `cargo test` succeeds with:
  ```
  test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
  ```
- Running the Python tests via `uv run scripts/test.py -x --timeout=10 -q` completes successfully:
  ```
  830 passed, 40 warnings in 25.71s
  ```

---

## 2. Logic Chain
1. **Animator Definition**: The Rust equivalent of the animation configuration and runtime state must support frames, speed, loop, and ping-pong (from observations of `AnimationDefinition` and `Animator` on the Python side).
2. **Animation Index Mapping**: In Bevy 0.19, `Sprite` integrates the texture atlas via `sprite.texture_atlas: Option<TextureAtlas>` where `TextureAtlas` stores `index: usize`. Therefore, advancing frames in Bevy means incrementing the active frame index in `sprite.texture_atlas.as_mut().unwrap().index`.
3. **Synchronization Logic**: The sync system must match the Python version's logic of lowercase mapping `ai_state.current_action` and applying `Flight` overrides (swapping to `"swoop"` or `"fly"` depending on `flight.flight_state` non-grounded values).
4. **Command Execution & Lock**: Directly mapping `CommandType::PlayAnimation` in `apply_ai_commands` requires setting `animator.current_animation = anim_name`. To prevent the `sync_yukkuri_animations` system from immediately overwriting this change back to the current AI action in the same frame, we need a locking mechanism: a `manual_override: bool` flag and `ai_action_at_override: String` tracker on `Animator`.

---

## 3. Caveats
- This investigation assumes that the asset loader (Milestone 1) will attach the initial Bevy `Sprite` and `Animator` components to the yukkuri prefab entity.
- Coordinate conversion is not required for `PlayAnimation` commands because animations do not depend on screen or world coords.

---

## 4. Conclusion
We have designed a complete, thread-safe, and backward-compatible FFI command parsing and AIState/flight state sync system. Implementing `AnimationDefinition`, `Animator`, and systems (`update_animator_system`, `sync_yukkuri_animations`) in Bevy's `Update` schedule using `Time<Virtual>` will fulfill all R2 requirements.

---

## 5. Verification Method
1. **Cargo Test suite**:
   ```powershell
   cargo test
   ```
2. **Integration Test Verification**:
   Ensure `tests/migration_test.rs` or a new test under `tests/` registers the new systems, spawns a prefab, injects a `PlayAnimation` FFI command (verifying `manual_override` remains locked), updates the flight state (verifying it plays `"fly"` or `"swoop"` when airborne), and checks that events are fired.
