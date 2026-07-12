# Original User Request

## Initial Request — 2026-06-20T02:34:31Z

Port the *Yukkuri Raising Game* simulation core and game loop to Bevy 0.19 and Rust, using PyO3 to embed the Python interpreter to run the existing AI Behavior Trees via Blackboard/Command FFI.

Working directory: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game
Integrity mode: development

## Requirements

### R1. Rust Project Initialization & Bevy 0.19 Setup
- Initialize a Cargo binary project in the repository root.
- Add dependencies for `bevy` (v0.19), `avian2d` (v0.1 or compatible 2D physics), `pyo3` (with features `extension-module` or `auto-initialize` as appropriate for embedding), `serde`, `serde_json`, and `toml`.
- Configure the binary in `src/main.rs` to start a basic game loop.

### R2. PyO3 FFI Boundary & Rust Structs
- Implement the Rust equivalents of the FFI structures specified in Section 2 of `docs/bevy_rust_migration_guide.md`:
  - `TargetInfo`: Contains `entity_id` (u32), `stable_id` (u64), `type_id` (String), `growth_stage` (String), `x` (f32), `y` (f32), `distance` (f32), `affinity` (f32), `is_threat` (bool), `is_prey` (bool), `is_family` (bool), `tags` (HashSet<String>).
  - `Blackboard`: Contains `entity_id` (u32), `stats` (HashMap<String, f32>), `x` (f32), `y` (f32), `altitude` (f32), `flight_state` (u32), `visible_targets` (Vec<TargetInfo>), `current_action` (String), `short_term_memory` (HashMap<u32, (f32, f32, f32)>).
  - `CommandType`: Enum containing variants `MoveTo`, `Flee`, `Speak`, `PlayAnimation`, `Attack`, `Interact`, `ModifyStat`.
  - `Command`: Contains `cmd_type` (CommandType), `entity_id` (u32), `payload` (HashMap<String, String>).
- Expose these structs and enums to Python using PyO3 `#[pyclass]` and `#[pymethods]` macros so they can be exchanged.
- **Coordinate Conversion**: Handle Y-axis coordinate conversion at the FFI boundary between Pygame's Y-down and Bevy's Y-up system using:
  $$\text{Python } y = \text{World Height} - \text{Bevy } y$$

### R3. Python World Adapter (`BevyWorldAdapter`) & Entry Point
- **Expose FFI Entry Point**: Implement a python function `tick_entity_with_blackboard(blackboard: Blackboard) -> list[Command]` inside `src/yukkuri_game/game/systems/behavior.py` (or a dedicated FFI module).
- **World Adapter**: Implement a lightweight `BevyWorldAdapter` to intercept behavior tree action node queries (like `self.world.try_get_component` and `self.world.services.try_get`).
  - Intercept and mock components: `Transform` (mapped to blackboard `x`, `y`), `Needs` / `YukkuriStats` (mapped to `blackboard.stats`), `AIState`, and the `Blackboard` component.
  - Intercept and mock services: `NavigationService` (to immediately set `ai.path = [target_pos]` so trees don't hang), `GameService`, `TimeService`, and `TraitService` (using the real pure-logic `TraitService`).
  - This allows the existing behavior tree nodes to run completely unchanged without requiring rewriting.

### R4. Thread-Safe GIL Scheduling, Ticking, & Command Dispatcher
- **GIL Safety**: Schedule the Python AI ticking system sequentially or as a single-threaded Bevy system (using `NonSend` resource or thread-local scheduling) to prevent multi-threaded GIL deadlocks or panics.
- **Fixed vs Variable Ticking**: Ticking the Python behavior trees must run in the variable update schedule (`Update` system set). Avian physics updates must run in the fixed time-step schedule (`FixedUpdate` system set).
- **Command Dispatcher**: Implement a Bevy system (`apply_ai_commands`) that pops queued commands returned by the Python AI and maps them to physics/gameplay state changes:
  - `MoveTo`: Insert a `MoveTarget` component on the entity with coordinates and acceptance radius.
  - `Flee`: Adjust velocity/forces directly.
  - `ModifyStat`: Mutate needs/stats components.

### R5. TOML Archetype (Prefab) Loader
- Implement a Rust system that loads and deserializes TOML prefabs (like `data/prefabs/reimu.toml`) into a `YukkuriPrefab` structure using Serde.
- Build a spawning utility that uses the prefab to spawn Bevy entities with the correct Avian physics collider, mass, friction, and needs components.

## Verification Plan

### Automated Tests
- Write a Rust integration test in `tests/migration_test.rs` that:
  - Initializes a Bevy app headless.
  - Spawns a Yukkuri entity from a TOML prefab.
  - Configures the Python AI behavior modules to return a test command (e.g. `MOVE_TO`).
  - Ticks the app and asserts that the `Blackboard` was successfully constructed and passed to Python, and that the resulting `Command` was popped and executed (updating the entity's Bevy components/physics state).
  - Run with:
    ```powershell
    cargo test --test migration_test
    ```

## Acceptance Criteria

### Compilation and Execution
- [ ] The Rust project compiles successfully without warnings or errors.
- [ ] `cargo test --test migration_test` passes.
- [ ] PyO3 correctly embeds the local Python virtual environment without linking errors.
- [ ] All code conforms to safe Rust patterns and the Python/Rust interface is clean and thread-safe.

## Follow-up — 2026-06-21T00:04:56Z

Port the *Yukkuri Raising Game* simulation core and game loop to Bevy 0.19 and Rust, using PyO3 to embed the Python interpreter to run the existing AI Behavior Trees via Blackboard/Command FFI.

Working directory: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game
Integrity mode: development

References:
- Avian 2D Migration Guide (0.6 to 0.7): https://github.com/avianphysics/avian/blob/main/migration-guides/0.6-to-0.7.md

## Requirements

### R1. Rust Project Initialization & Bevy 0.19 Setup
- Initialize a Cargo binary project in the repository root.
- Add dependencies for `bevy` (v0.19), `avian2d` (v0.7.0), `pyo3` (with features `extension-module` or `auto-initialize` as appropriate for embedding), `serde`, `serde_json`, and `toml`.
- Configure the binary in `src/main.rs` to start a basic game loop.

### R2. PyO3 FFI Boundary & Rust Structs
- Implement the Rust equivalents of the FFI structures specified in Section 2 of `docs/bevy_rust_migration_guide.md`:
  - `TargetInfo`: Contains `entity_id` (u32), `stable_id` (u64), `type_id` (String), `growth_stage` (String), `x` (f32), `y` (f32), `distance` (f32), `affinity` (f32), `is_threat` (bool), `is_prey` (bool), `is_family` (bool), `tags` (HashSet<String>).
  - `Blackboard`: Contains `entity_id` (u32), `stats` (HashMap<String, f32>), `x` (f32), `y` (f32), `altitude` (f32), `flight_state` (u32), `visible_targets` (Vec<TargetInfo>), `current_action` (String), `short_term_memory` (HashMap<u32, (f32, f32, f32)>).
  - `CommandType`: Enum containing variants `MoveTo`, `Flee`, `Speak`, `PlayAnimation`, `Attack`, `Interact`, `ModifyStat`.
  - `Command`: Contains `cmd_type` (CommandType), `entity_id` (u32), `payload` (HashMap<String, String>).
- Expose these structs and enums to Python using PyO3 `#[pyclass]` and `#[pymethods]` macros so they can be exchanged.
- **Coordinate Conversion**: Handle Y-axis coordinate conversion at the FFI boundary between Pygame's Y-down and Bevy's Y-up system using:
  $$\text{Python } y = \text{World Height} - \text{Bevy } y$$

### R3. Python World Adapter (`BevyWorldAdapter`) & Entry Point
- **Expose FFI Entry Point**: Implement a python function `tick_entity_with_blackboard(blackboard: Blackboard) -> list[Command]` inside `src/yukkuri_game/game/systems/behavior.py` (or a dedicated FFI module).
- **World Adapter**: Implement a lightweight `BevyWorldAdapter` to intercept behavior tree action node queries (like `self.world.try_get_component` and `self.world.services.try_get`).
  - Intercept and mock components: `Transform` (mapped to blackboard `x`, `y`), `Needs` / `YukkuriStats` (mapped to `blackboard.stats`), `AIState`, and the `Blackboard` component.
  - Intercept and mock services: `NavigationService` (to immediately set `ai.path = [target_pos]` so trees don't hang), `GameService`, `TimeService`, and `TraitService` (using the real pure-logic `TraitService`).
  - This allows the existing behavior tree nodes to run completely unchanged without requiring rewriting.

### R4. Thread-Safe GIL Scheduling, Ticking, & Command Dispatcher
- **GIL Safety**: Schedule the Python AI ticking system sequentially or as a single-threaded Bevy system (using `NonSend` resource or thread-local scheduling) to prevent multi-threaded GIL deadlocks or panics.
- **Fixed vs Variable Ticking**: Ticking the Python behavior trees must run in the variable update schedule (`Update` system set). Avian physics updates must run in the fixed time-step schedule (`FixedUpdate` system set).
- **Command Dispatcher**: Implement a Bevy system (`apply_ai_commands`) that pops queued commands returned by the Python AI and maps them to physics/gameplay state changes:
  - `MoveTo`: Insert a `MoveTarget` component on the entity with coordinates and acceptance radius.
  - `Flee`: Adjust velocity/forces directly.
  - `ModifyStat`: Mutate needs/stats components.

### R5. TOML Archetype (Prefab) Loader
- Implement a Rust system that loads and deserializes TOML prefabs (like `data/prefabs/reimu.toml`) into a `YukkuriPrefab` structure using Serde.
- Build a spawning utility that uses the prefab to spawn Bevy entities with the correct Avian physics collider, mass, friction, and needs components.

## Verification Plan

### Automated Tests
- Write a Rust integration test in `tests/migration_test.rs` that:
  - Initializes a Bevy app headless.
  - Spawns a Yukkuri entity from a TOML prefab.
  - Configures the Python AI behavior modules to return a test command (e.g. `MOVE_TO`).
  - Ticks the app and asserts that the `Blackboard` was successfully constructed and passed to Python, and that the resulting `Command` was popped and executed (updating the entity's Bevy components/physics state).
  - Run with:
    ```powershell
    cargo test --test migration_test
    ```

## Acceptance Criteria

### Compilation and Execution
- [ ] The Rust project compiles successfully without warnings or errors.
- [ ] `cargo test --test migration_test` passes.
- [ ] PyO3 correctly embeds the local Python virtual environment without linking errors.
- [ ] All code conforms to safe Rust patterns and the Python/Rust interface is clean and thread-safe.

## Follow-up — 2026-06-29T21:52:39Z

Port the biological, social, and environmental simulation systems from Python to the Rust/Bevy codebase, integrating them with Bevy 0.19, Avian 2D v0.7.0, and the PyO3 behavior tree environment.

Working directory: `c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game`
Integrity mode: benchmark

## Requirements

### R1. Need Decay, Metabolism, and Waste Simulation
- Implement tick systems in Bevy for decay of `hunger`, `energy`, `social`, `cleanliness`, and `bladder` components.
- Apply starvation damage when `hunger` reaches 100%.
- Implement chance-based pooping based on time and bladder levels.
- Spawn poop entities, decrease cleanliness of nearby entities (spatial checks), and implement player cleanliness cleanup commands.

### R2. Lifecycle and Breeding
- Age ticking system transitioning through `Baby` -> `Child` -> `Adult` stages.
- Adjust entity scale factor and physical collider size in Bevy/Avian on stage transition.
- Check and roll breeding chances for happy/energetic adults.

### R3. Proximity, Gossip, and Relationship Systems
- Register family relationships and apply Proximity Benefits (happiness gain/stress drop when near family).
- Implement Opinion/Gossip systems tracking interpersonal relationship stats (affinity, trust, fear, familiarity) and transmitting witnessed events within a radius.

### R4. Traits and Skills
- Modify need decay rates, behavior tree choices, and utility evaluation curves based on personality traits.
- Track XP gain/decay for skills like `scavenging` and `athletics` based on passion levels and intelligence.

### R5. Physics, Movement, and Navigation Grid
- Handle mounting/dismounting with collision-free spiral searches.
- Implement Inventory tracking, physical item pickup/drop, and HUD sync.
- Dynamic collision modulation based on flight/grounded state.
- Pathfinding (navigation grid updates, HPA cluster rebuilding).
- Visual hopping/bobbing (sine-wave vertical offset) during movement.

### R6. Time and Environment Systems
- Time synchronization (virtual clock scaling, day count, hour of day) exposed to PyO3 blackboard.
- Day/Night cycle rendering with color ramp interpolation and Bevy 2D light overlays.
- Cursor light toggling and Darkness stress accumulation for entities not near a light source.
- Auditory/Visual feedback systems (ambient crying, floating text overlays, sound bindings).

### R7. Player Interactions and Shop
- Sell, Train, and Punish player commands (deducting/adding funds, health, stress, badges).
- Shop/Placement system for spawning items (cookies, beds, toys).
- Predation and interactive events (eating/speaking/dodging checks).
- Level of Detail (LOD) simulation throttling based on camera distance.

### R8. Project Constraints
- **GIL Safety**: Schedule PyO3-embedded Python updates as a single-threaded/exclusive system (using Bevy's `NonSend` resource or thread-local system scheduling) to prevent concurrent GIL acquisition deadlocks. Acquire the GIL once per frame during the AI tick system.
- **Coordinate Conversion**: Translate coordinates at the FFI boundary using `Python y = World Height - Bevy y` for Blackboard building and `MOVE_TO`/`FLEE` dispatching.
- **Python World Adapter Caching**: Do not instantiate a fresh adapter on every tick if the behavior tree is cached; update blackboard data in-place or traverse nodes to update the `world` reference.
- **Bevy 0.19 / Avian 2D API**:
  - `MoveAndSlide::intersections` callback must accept the third `Entity` parameter.
  - Avoid multiple queries accessing the same component mutably, or both mutably and immutably, in the same system without disjoint filters or `ParamSet`.
  - Use `MessageWriter`/`MessageReader` instead of `EventWriter`/`EventReader`.
  - Use `commands.entity(entity).despawn()` for recursive despawning and `.despawn_related::<Children>()` for descendants.
  - String arguments for PyO3: `py.eval` and `py.run` require `&CStr`.

## Acceptance Criteria

### Compilation & Tests
- [ ] Code compiles cleanly on Windows with Rust 2021 edition and Bevy 0.19.
- [ ] All existing tests in `tests/` pass successfully.
- [ ] New unit tests covering need decay, poop spawning, lifecycle transitions, and social affinity systems are added under `tests/` and pass.

### FFI & Coordinate Integration
- [ ] Coordinates are correctly translated when passed to/from the behavior tree.
- [ ] Python AI ticks execute without GIL deadlocks or stale adapter references.
