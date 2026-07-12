## 2026-06-20T19:44:12Z

Please implement Milestones 5 and 6 of the Bevy-Rust migration plan.

1. **Create the Prefab Config File**:
   - Create a file at `data/prefabs/reimu.toml` containing:
     ```toml
     [prefab]
     type_id = "reimu"
     name = "Reimu Yukkuri"
     growth_stage = "Adult"

     [physics]
     radius = 20.0
     mass = 1.5
     friction = 0.8
     restitution = 0.2

     [needs]
     max_health = 100.0
     energy = 100.0
     hunger = 0.0
     max_stamina = 100.0

     [steering]
     max_speed = 150.0
     max_force = 500.0
     arrival_radius = 50.0
     ```

2. **Implement TOML Archetype Loader & Spawning Utility**:
   - In `src/prefabs/mod.rs`, implement deserialization logic for the prefab structure:
     - `YukkuriPrefab` containing `prefab: PrefabHeader`, `physics: PhysicsPrefab`, `needs: NeedsPrefab`, `steering: SteeringPrefab`.
     - Implement `load_prefab(path: &str) -> Result<YukkuriPrefab, Box<dyn std::error::Error>>` using `std::fs::read_to_string` and `toml::from_str`.
     - Implement `spawn_yukkuri_prefab(commands: &mut Commands, prefab: &YukkuriPrefab, position: Vec2)` which spawns a Bevy entity and inserts:
       - `Transform::from_xyz(position.x, position.y, 0.0)`
       - `Visibility::default()`
       - `avian2d::prelude::RigidBody::Dynamic`
       - `avian2d::prelude::Collider::circle(prefab.physics.radius)`
       - `avian2d::prelude::Mass(prefab.physics.mass)`
       - `avian2d::prelude::Friction::new(prefab.physics.friction)`
       - `avian2d::prelude::Restitution::new(prefab.physics.restitution)`
       - Gameplay components from `src/ai/mod.rs`: `Needs`, `YukkuriStats`, `EmotionalState`, `AIState`, `Flight`, `VisibleTargets`. Use fields from the loaded TOML config.

3. **Register modules and plugins in `src/main.rs`**:
   - Declare `mod prefabs;` in `src/main.rs`.
   - Update `main` in `src/main.rs` to register `ai::AIPlugin` with the Bevy App (`.add_plugins(ai::AIPlugin)`).

4. **Implement the Integration Test (`tests/migration_test.rs`)**:
   - Write a Rust integration test `tests/migration_test.rs` that:
     - Prepares free-threaded python using `pyo3::prepare_freethreaded_python()` and appends `yukkuri_rust` to inittab before initialization.
     - Initializes a Bevy app headless (`MinimalPlugins`, `avian2d::prelude::PhysicsPlugins::default()`).
     - Adds `ai::AIPlugin`.
     - Loads the `reimu.toml` prefab file.
     - Spawns a Yukkuri entity from the prefab at a specific coordinate (e.g. `x = 100.0, y = 100.0`).
     - Configures the entity's needs/stats so that the behavior tree ticks and executes. (Note: behavior tree will naturally tick Wander/Idle or search for food/toy depending on stats; high hunger triggers forage/eat which publishes a MoveTo command to the closest food item).
     - Run `app.update()` to tick the system.
     - Asserts that the entity has been spawned with correct physics components.
     - Asserts that the FFI executed, returned commands, and the dispatcher popped them and executed them (e.g. generating `MoveTarget` component on the entity).

5. **Verify and Run Tests**:
   - Run `cargo test --test migration_test` to verify that the FFI integration works perfectly.
   - Run the full project tests to ensure no regressions are introduced.
   - Write progress and handoff report to `.agents/worker_milestone5_6/handoff.md`.
