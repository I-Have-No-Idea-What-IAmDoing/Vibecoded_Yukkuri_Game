## 2026-06-29T22:02:09Z
You are the Worker subagent for Milestone 1: Need Decay, Metabolism, and Waste Simulation.
Your task is to implement the biological, metabolism, and waste simulation systems in Bevy and verify them.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT
hardcode test results, create dummy/facade implementations, or
circumvent the intended task. A Forensic Auditor will independently
verify your work. Integrity violations WILL be detected and your
work WILL be rejected.

Please execute the following steps precisely:
1. Create `src/simulation/needs.rs` implementing:
   - `Poop` component (marker struct with reflection derive).
   - `CleanPoopMessage` message struct (using `#[derive(Message, Debug, Clone)]` conforming to Bevy 0.19 events/messages rules).
   - `SimulationSettings` resource containing default values matching the Python decay/poop rules:
     - `hunger_decay_rate`: 2.0 (hunger increases by this per game second)
     - `energy_decay_rate`: 0.5 (energy decreases by this per game second)
     - `cleanliness_decay_rate`: 0.2 (cleanliness decreases by this per game second)
     - `social_decay_rate`: 0.5 (social need decreases by this per game second)
     - `starvation_damage_rate`: 5.0 (health decreases by this per game second when hunger >= 100.0)
     - `time_scale`: 60.0 (virtual time scale to multiply Virtual Time delta_secs())
     - `poop_spawn_chance`: 0.01 (base random poop chance per physics/real second)
     - `bladder_full_threshold`: 80.0
     - `bladder_full_chance_mult`: 10.0
     - `cleanliness_critical_threshold`: 10.0
     - `cleanliness_critical_chance_mult`: 5.0
     - `spawn_cleanliness_penalty`: 5.0
     - `spawn_offset_range`: 10.0
     - `poop_smell_radius`: 200.0
     - `poop_smell_strength`: 5.0 (cleanliness decreases by this per real/physics second when in radius)
   - Bevy systems:
     - `needs_decay_tick_system`: Ticks hunger, energy, cleanliness, social using virtual time (`Res<Time<Virtual>>`) and applying `time_scale` to get `game_dt`. Applies starvation damage when `hunger` reaches 100.0. Clamps values appropriately.
     - `poop_spawning_system`: Evaluates poop spawning chance-based checks (base chance, bladder full, cleanliness critical) using real delta-time, spawns poop entities with coordinates offset by `spawn_offset_range`, decreases cleanliness by penalty, and resets bladder to 0.0. Poops should spawn as Bevy entities with `Transform` (with z = 1.0), `Sprite` (with `image: asset_server.load("images/poop.png")`), `RigidBody::Dynamic`, `Collider::circle(10.0)`, `Mass(1.0)`, `Friction::new(0.2)`, `Restitution::new(0.2)`, and `Poop`.
     - `poop_cleanliness_reduction_system`: Uses disjoint queries to prevent B0001 Panics (e.g. `poop_query: Query<&Transform, (With<Poop>, Without<Needs>)>`, `yukkuri_query: Query<(&Transform, &mut Needs), (Without<Poop>, With<Needs>)>`). Deducts cleanliness for nearby entities within smell radius by `poop_smell_strength * dt`.
     - `handle_clean_poop_message_system`: Listens to `CleanPoopMessage` and despawns all `Poop` entities within `CleanPoopMessage::radius` of `CleanPoopMessage::position`. Writes a `PlaySoundEvent` event/message with name `"click"` if any poop was cleaned.
     - `clean_poop_on_click_system`: Detects left mouse click while the `C` key is pressed, converts screen coords to world coords, and despawns any `Poop` entity within 32.0 units, writing `"click"` `PlaySoundEvent` if cleaned.
   - `NeedsSimulationPlugin` registering these systems, settings, and reflection components.

2. Create `src/simulation/mod.rs` containing a parent `SimulationPlugin` which adds `NeedsSimulationPlugin`.

3. Register `simulation` module in `src/lib.rs` and `SimulationPlugin` in `src/main.rs`.

4. Create integration tests in `tests/simulation_tests.rs` verifying:
   - Needs decay and starvation damage works correctly using `TimeUpdateStrategy::ManualDuration` to advance time deterministically.
   - Poop spawning, bladder resetting, and cleanliness penalty are applied correctly when bladder > 80.
   - Cleanliness reduction around poop entities works within radius, and does not affect distant entities.
   - Message-based `CleanPoopMessage` successfully cleans poops and despawns the entities.

5. Compile and run all tests (`cargo test` and `uv run scripts/test.py` if python tests are still needed) to ensure everything compiles and passes cleanly.

Write your handoff report detailing your implementation and test run output to `.agents/worker_1/handoff.md`.
Your working directory is: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_1
