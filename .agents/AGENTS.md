# Project Rules: Pygame-CE to Bevy & Rust Port

These rules apply when developing the Rust/Bevy host engine and PyO3-embedded Python behavior tree integration.

## 1. PyO3 Thread Safety & GIL Scheduling
- **Main Thread Execution**: Always schedule PyO3-embedded Python updates as a single-threaded/exclusive system (using Bevy's `NonSend` resource or thread-local system scheduling) to prevent concurrent GIL acquisition deadlocks or panics.
- **Acquire GIL Once Per Frame**: Acquire the GIL once per frame during the AI tick system, iterate over active entities, and process their behavior trees sequentially.

## 2. Coordinate System Translation
- **Coordinate Border Translation**: Translate coordinates at the FFI boundary between Pygame's Y-down origin and Bevy's Y-up origin using:
  $$\text{Python } y = \text{World Height} - \text{Bevy } y$$
  Ensure both the `Blackboard` building and `MOVE_TO`/`FLEE` command dispatching apply this transformation.

## 3. Python World Adapter Caching & Closure Updates
- **Avoid Stale References**: When using a mock `World` adapter (`BevyWorldAdapter`) to tick Python behavior trees inside Bevy:
  - Do not instantiate a fresh adapter on every tick if the behavior tree is cached.
  - Instead, update the adapter's blackboard data in-place (`update_blackboard()`), or traverse the behavior tree nodes to explicitly update their `world` reference to point to the active adapter instance.
  - This prevents leaf nodes from executing against a stale closure capture of the adapter.

## 4. Avian 2D v0.7 & Bevy 0.19 API Integration
- **Signature Conventions**: When writing Avian 2D systems under Bevy 0.19 (using Avian v0.7.0):
  - Ensure the `MoveAndSlide::intersections` callback accepts the third `Entity` parameter (e.g. `|_, _, entity|` or `|_, _, _|`).


## 5. Bevy 0.19 ECS Query & API Design Rules
- **Query Disjointness (B0001 Panics)**: When a system contains multiple queries accessing the same component mutably (e.g. `&mut Node`), or querying the same component both mutably and immutably (e.g. `&Needs` and `&mut Needs`), you must either use disjoint filters (like `With<A>` on one and `Without<A>` on another) or wrap them in a `ParamSet` (e.g. `ParamSet<(Query<&Needs>, Query<&mut Needs>)>`) to ensure Bevy's ECS validation does not panic on startup.
- **Message system (Formerly Events)**: In Bevy 0.19, `EventWriter` and `EventReader` have been renamed to `MessageWriter` and `MessageReader`. Send messages using `message_writer.write(msg)` and read them using `message_reader.read()`.
- **Hierarchy Despawning**: `despawn_recursive()` and `despawn_descendants()` have been removed. Use `commands.entity(entity).despawn()` (which is hierarchy-aware) to despawn recursively, and `commands.entity(entity).despawn_related::<Children>()` to despawn descendants only.
- **PyO3 0.23 String Arguments**: 
  - `py.eval(...)` and `py.run(...)` require `&CStr`. Use Rust `c"..."` for static literals, `cr#"..."#` for raw C-string literals, or `std::ffi::CString` for dynamic strings.
  - Dict items (`set_item`) and module imports (`py.import`) still require standard `&str`.

The original python code can be found in the MVP_python branch. 
