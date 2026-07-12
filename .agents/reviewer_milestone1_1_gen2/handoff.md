# Handoff Report — Review of Milestone 1

This handoff report summarizes the findings of the Milestone 1 (Need Decay, Metabolism, and Waste Simulation) review.

## 1. Observation

- **Implementation File**: `src/simulation/needs.rs`
  - Defines `SimulationSettings` resource for configurable rates and thresholds (lines 20-60).
  - Implements `needs_decay_tick_system` applying hunger, energy, cleanliness, and social decay, as well as starvation damage using virtual time (lines 64-83).
  - Implements `poop_spawning_system` based on periodic chance, bladder thresholds, and cleanliness critical thresholds (lines 88-152).
  - Implements `poop_cleanliness_reduction_system` to decrease cleanliness for nearby entities using disjoint queries (lines 156-178).
  - Implements `handle_clean_poop_message_system` responding to `CleanPoopMessage` and playing "click" sound (lines 182-204).
  - Implements `clean_poop_on_click_system` converting screen coordinates to world coordinates to despawn poop on mouse click while holding `C` (lines 208-248).
- **Test File**: `tests/simulation_tests.rs`
  - Defines 4 tests: `test_needs_decay_and_starvation`, `test_poop_spawning_on_bladder_full`, `test_cleanliness_reduction_near_poop`, and `test_clean_poop_message`.
- **FFI & Coordinate Mapping Files**:
  - `src/ai/mod.rs`: `tick_python_ai_system` uses `NonSend<PythonAISandbox>` and wraps sequential ticks inside a single `Python::with_gil` acquisition per frame (lines 459, 481).
  - `src/ai/blackboard.rs`: `TargetInfo::from_bevy` and `Blackboard::from_bevy` convert Bevy coordinates to Python using `python_y = world_height - bevy_y` (lines 88, 184).
  - `src/ai/commands.rs`: `Command::get_bevy_coordinate` converts Python coordinates back to Bevy using `bevy_y = world_height - py_y` (line 48).
  - `src/ai/mod.rs` (Flee Command): `bevy_vy = -py_vy` is applied to flip vertical velocity (line 660).
- **Test Execution Results**:
  - Running `cargo test --test simulation_tests` completes successfully with output:
    ```
    running 4 tests
    test test_clean_poop_message ... ok
    test test_cleanliness_reduction_near_poop ... ok
    test test_poop_spawning_on_bladder_full ... ok
    test test_needs_decay_and_starvation ... ok
    test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.08s
    ```
  - Running `uv run scripts/test.py -x --timeout=10 -q` completes successfully with output:
    ```
    922 passed, 40 warnings in 51.15s
    ```

---

## 2. Logic Chain

- **Decay & Metabolism Correctness**: The `needs_decay_tick_system` uses virtual time delta-seconds multiplied by `time_scale` to update hunger, energy, cleanliness, and social stats. When hunger reaches `100.0`, health is reduced by `starvation_damage_rate`. This matches the requirement to simulate physical need decay and starvation damage.
- **Waste & Spawning Correctness**: The `poop_spawning_system` runs on real delta time and evaluates three independent random triggers (base, bladder threshold, and cleanliness critical). If any triggers, it spawns a poop entity (with sprite and physical properties), applies a cleanliness penalty to the Yukkuri, and resets bladder to `0.0`. This correctly models the metabolism and waste generation logic.
- **B0001 Panic Prevention (Disjointness)**: The `poop_cleanliness_reduction_system` queries:
  - `poop_query: Query<&Transform, (With<Poop>, Without<Needs>)>`
  - `yukkuri_query: Query<(&Transform, &mut Needs), (Without<Poop>, With<Needs>)>`
  Because these queries use disjoint filter sets (`With<Poop>, Without<Needs>` and `Without<Poop>, With<Needs>`) and only one query accesses `Needs` mutably while `Transform` is accessed immutably in both, they are disjoint and do not cause a borrow checker or Bevy ECS validation panic (B0001).
- **FFI & FFI Rule Conformance**: `tick_python_ai_system` uses Bevy's `NonSend` resource scheduling to run exclusively on the main thread and secures the Python GIL exactly once per frame, sequentially ticking active behavior trees.
- **Coordinate Border Translation**: Coordinates at the FFI boundary are translated using `y = World Height - Bevy y` for both blackboard serialization and command deserialization (`MoveTo` and `Flee`), fulfilling the coordinate border translation rules.
- **API Rules Compliance**: `needs.rs` uses `MessageReader` and `MessageWriter` instead of events, and `commands.entity(entity).despawn()` instead of `despawn_recursive()`, complying with the Bevy 0.19 migration guidelines.

---

## 3. Caveats

- **Click-to-Clean System Camera Assumptions**: `clean_poop_on_click_system` uses `camera_query.iter().next()` to obtain the camera and its global transform for screen-to-world projection. If the application spawns multiple active cameras (such as a separate UI overlay camera or developer inspector camera), this query could return a camera with the wrong projection, causing viewport translation to fail or return incorrect coordinates.
- **No click-to-clean tests**: There is currently no unit test coverage for `clean_poop_on_click_system` in `tests/simulation_tests.rs` due to the complexity of mocking viewport mapping and input states.

---

## 4. Conclusion

The implementation of Milestone 1 is functionally correct, clean, and complies with all custom constraints listed in `AGENTS.md` and Bevy 0.19 / Avian 2D v0.7.0 APIs. The code has been verified both via static analysis and test suite execution.

We issue a verdict of **APPROVE** with minor suggestions to improve the robustness of the camera query in `clean_poop_on_click_system`.

---

## 5. Verification Method

To verify the implementation and tests independently, run:
1. **Rust Simulation Tests**:
   ```powershell
   cargo test --test simulation_tests
   ```
   Ensures all decay, spawning, cleanliness reduction, and cleaning message tests pass.
2. **Python Test Suite**:
   ```powershell
   uv run scripts/test.py -x --timeout=10 -q
   ```
   Ensures no regressions are introduced into the Python integration layers.

---

# Quality Review Report

## Review Summary

**Verdict**: APPROVE

## Findings

### [Minor] Unfiltered Camera Query in Click-to-Clean System

- **What**: The click-to-clean system queries `(&Camera, &GlobalTransform)` without any filter tag.
- **Where**: `src/simulation/needs.rs` (lines 213, 225).
- **Why**: In multi-camera setups (e.g. game camera + UI camera), this query might return the wrong camera first, rendering coordinate projection incorrect.
- **Suggestion**: Add `With<MainCamera>` to the camera query, e.g.:
  `camera_query: Query<(&Camera, &GlobalTransform), With<MainCamera>>` (importing `MainCamera` from `crate::camera::MainCamera`).

## Verified Claims

- **GIL safety** → verified via inspecting `src/ai/mod.rs` lines 459, 481 → **PASS** (scheduled on exclusive system, GIL acquired once per frame).
- **Coordinate system translation** → verified via inspecting FFI boundary code in `src/ai/blackboard.rs` and `src/ai/commands.rs` → **PASS** (Y-up to Y-down FFI translation applied correctly).
- **Prevent B0001 panics** → verified via inspecting query disjointness in `needs.rs` lines 159-160 → **PASS** (disjoint filters used).
- **Event to Message rename** → verified via inspecting usages of `MessageReader`/`MessageWriter` in `needs.rs` → **PASS** (compliant with Bevy 0.19).

## Coverage Gaps

- **Click-to-Clean system testing** — risk level: low — recommendation: accept risk or add a unit test using mocked inputs.

## Unverified Items

- None (all items verified).

---

# Adversarial Challenge Report

## Challenge Summary

**Overall risk assessment**: LOW

## Challenges

### [Low] Assumption of Single-Camera in Mouse Click Coordinate Translation

- **Assumption challenged**: Assumes the first camera returned by `camera_query.iter().next()` is the main world camera.
- **Attack scenario**: An overlay or viewport UI camera is registered before the main camera. When the user holds `C` and left-clicks, coordinates are projected through the UI camera's orthographic projection, yielding incorrect world coordinates, and causing poop cleaning clicks to miss.
- **Blast radius**: The user will be unable to clean poop via clicking in-game.
- **Mitigation**: Filter the camera query using the `MainCamera` component marker.

## Stress Test Results

- **High-frequency updates** → Decay and starvation damage calculations remain correct even with large virtual delta-times, as clamp limits `health` to `[0.0, max_health]` and needs to `[0.0, 100.0]`. → **PASS**

## Unchallenged Areas

- **Despawning behavior of complex structures**: We assumed poop has no child entities that would be leaked by calling `.despawn()` instead of recursively despawning. This is correct since poop is a single flat entity.
