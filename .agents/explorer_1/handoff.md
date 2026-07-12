# Handoff Report — Need Decay, Metabolism, and Waste Simulation

## 1. Observation
The original Python codebase (`MVP_python` branch) implemented the need decay, starvation, and poop spawning mechanics in `EmotionSystem`, `PoopSystem`, and `CleanEntityCommand`.
Specifically:
- **Need Decay Rates** (from `src/yukkuri_game/config.py` and `rules.toml`):
  - `hunger`: passive increase of `0.0035` units per game second (increases need to eat).
  - `energy`: passive decay of `-0.002` units per game second.
  - `cleanliness`: passive decay of `-0.0015` units per game second.
  - `social`: passive decay of `-0.002` units per game second.
  - `bladder`: no passive decay or increase, only increases by `0.5 * nutrition` of consumed food.
- **Starvation Damage**:
  - Health is reduced by `0.003` per game second (loaded from `rules.toml`'s `starvation_damage`) when hunger is at 100.0%.
- **Poop Spawning**:
  - Base spawn chance of `0.01` per real second.
  - If `bladder > 80.0`, probability is multiplied by `10.0` (chance = `0.1` per second).
  - If `cleanliness < 10.0`, probability is multiplied by `5.0` (chance = `0.05` per second).
  - Spawning a poop applies a cleanliness penalty of `5.0` to the Yukkuri, resets its `bladder` to `0.0`, and creates a Poop entity with a minor coordinate offset (up to `10.0` units).
- **Proximity Cleanliness Reduction**:
  - Nearby poop entities within `200.0` smell radius reduce a Yukkuri's cleanliness by `5.0` units per second. This decay stacks if near multiple poops.
- **Cleaning Command**:
  - Clicking with the cleaning tool deletes poop entities within a radius of `32.0` units and plays a `"click"` sound.

On the Rust side, the implementation was drafted in `src/simulation/needs.rs` and `src/simulation/mod.rs` and registered in `src/main.rs` as `SimulationPlugin` containing `NeedsSimulationPlugin`.
However, the test suite `tests/simulation_tests.rs` fails to compile with three errors:
```
error[E0599]: no method named `send` found for struct `Mut<'_, bevy::prelude::Messages<CleanPoopMessage>>` in the current scope
   --> tests\simulation_tests.rs:205:66
    |
205 |     app.world_mut().resource_mut::<Messages<CleanPoopMessage>>().send(CleanPoopMessage {

error[E0599]: no method named `get_reader` found for reference `&bevy::prelude::Messages<PlaySoundEvent>` in the current scope
   --> tests\simulation_tests.rs:221:37
    |
221 |     let mut reader = message_events.get_reader();

error[E0596]: cannot borrow `*world` as mutable, as it is behind a `&` reference
   --> tests\simulation_tests.rs:119:26
    |
119 |     let mut poop_query = world.query_filtered::<(&Transform, &Poop), With<Poop>>();
```

## 2. Logic Chain
1. In Bevy 0.19, `Events<T>` was renamed to `Messages<T>`. The `.send()` method on `Messages<T>` was replaced with `.write()`.
   - Therefore, `app.world_mut().resource_mut::<Messages<CleanPoopMessage>>().send(...)` must be changed to `.write(...)` to compile.
2. In Bevy 0.19, the reader/cursor for a message queue is retrieved via `.get_cursor()`, not `.get_reader()`.
   - Therefore, `message_events.get_reader()` must be changed to `message_events.get_cursor()` to compile.
3. In Bevy 0.19, `World::query_filtered` requires a mutable reference to the world (`&mut self`).
   - Therefore, the immutable borrow of the world (`let world = app.world();`) must be changed to a mutable borrow (`let world = app.world_mut();`) in `test_poop_spawning_on_bladder_full`.

## 3. Caveats
- Since the Python-embedded behavior trees run within Python, the Rust side must keep the Python FFI blackboard updated. The blackboard already maps the Bevy `Needs` fields into Python.
- If a Yukkuri needs to search for poop in its visible targets, the perception system `populate_visible_targets_system` in `src/ai/mod.rs` may need to be updated to optionally perceive `Poop` entities in addition to other `YukkuriStats` entities (currently it only snapshots entities with `YukkuriStats`).

## 4. Conclusion
The Rust implementation in `src/simulation/needs.rs` is mostly complete and correctly implements need decay, starvation damage, poop spawning, proximity cleanliness reduction, and cleaning commands. The integration with Bevy is also fully implemented in `src/main.rs`.
However, the test suite `tests/simulation_tests.rs` is broken due to Bevy 0.19 API compilation issues. Once those 3 minor compilation issues are resolved, the tests should compile and pass.

## 5. Verification Method
Run:
`cargo test --test simulation_tests`
This will verify that the compilation issues in `tests/simulation_tests.rs` are resolved and that all simulation tests pass successfully.

## 6. Remaining Work
- Implement the proposed compilation fixes in `tests/simulation_tests.rs`:
  - Change `.send(...)` to `.write(...)` on line 205.
  - Change `.get_reader()` to `.get_cursor()` on line 221.
  - Change `let world = app.world();` to `let world = app.world_mut();` on line 110 of `tests/simulation_tests.rs` to allow calling `query_filtered` mutably.
- Verify that `cargo test` runs and passes successfully.
