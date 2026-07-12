# Analysis Report & Bevy-Rust FFI Migration Plan

## 1. Executive Summary

This report outlines the analysis and implementation plan to integrate a Bevy/Avian2d-based simulation engine in Rust with the existing Python-based behavior trees and AI logic. 

To preserve the complex behavior trees defined in Python via `py_trees`, we propose a **hybrid FFI architecture**:
1. **Bevy** runs the main simulation loop, tracks physical coordinates (Y-up), handles collisions via **Avian2d**, and manages entity lifecycles.
2. For entity decision-making, Bevy constructs a `Blackboard` snapshot for each active entity, converting vertical coordinates to the Python-expected system (Y-down).
3. Bevy safely calls a Python FFI entry point, `tick_entity_with_blackboard(blackboard)`, while managing the Global Interpreter Lock (GIL).
4. A Python **`BevyWorldAdapter`** intercepts the FFI call, mocking the expected ECS `World` environment, including components (`Needs`, `AIState`, `YukkuriStats`, `Transform`) and services (`CommandQueue`), allowing the existing behavior trees to run unchanged.
5. Commands produced by the behavior tree (such as `MOVE_TO`, `FLEE`, etc.) are captured by the mocked `CommandQueue`, converted into Rust-compatible structs, and returned to Bevy for execution in the physics/game world.

---

## 2. Current Python Codebase Examination

### 2.1 AI State and Blackboard Components

- **`AIState`** (defined in `src/yukkuri_game/game/components/social.py`):
  Stores transient runtime execution state for the AI, such as `current_action`, `current_target_id`, `path`, `action_progress`, `failed_targets`, and `visible_entities`. It also tracks `action_cooldowns` and a `decision_history` deque.
- **`Needs`** (defined in `src/yukkuri_game/game/components/social.py`):
  Tracks physiological needs: `max_health`, `health`, `hunger`, `social`, `energy`, `cleanliness`, `bladder`, and `easiness`. These values are clamped between 0 and 100 (or `max_health`).
- **`YukkuriStats`** (defined in `src/yukkuri_game/game/components/yukkuri.py`):
  Holds progression and species metrics: `name`, `type_id`, `age`, `growth_stage`, `badges`, `quality_score`, `discipline`, `intelligence`, `agility`, and `tastebud_spoiled`.
- **`Blackboard` & `TargetInfo`** (defined in `src/yukkuri_game/game/ai/blackboard.py`):
  Perception snapshots passed to the AI brain. `TargetInfo` contains positions (`x`, `y`), species/type data, and relationship metadata (`affinity`, `is_threat`, `is_prey`, `is_family`). `Blackboard` aggregates this along with the ticking entity's position, altitude, flight state, and short-term memory mapping.

### 2.2 Behavior Tree Ticking & Scheduling

Currently, `BehaviorSystem` (in `src/yukkuri_game/game/systems/behavior.py`) ticks behavior trees sequentially:
1. It instantiates behavior trees via `create_yukkuri_behavior_tree` for new entities and maintains them in a dictionary mapping entity IDs to trees.
2. It uses round-robin scheduling, throttling, and Level of Detail (LOD) multipliers to restrict ticks for stable (e.g., sleeping) or far-away entities.
3. It sets a global `"dt"` on the `py_trees.blackboard.Blackboard` and invokes `tree.tick()`.
4. Behaviors publish commands by calling `self.publish_command(CommandType, payload)`. This fetches the `CommandQueue` service from the world and pushes a `Command` object containing the command type, entity ID, and arguments.

---

## 3. Rust FFI Design (PyO3 & Coordinate Conversion)

### 3.1 Cargo Project Setup
Create a new Rust dynamic library crate (e.g., `yukkuri_bevy`) inside the repository.

**`Cargo.toml`**:
```toml
[package]
name = "yukkuri_bevy"
version = "0.1.0"
edition = "2021"

[lib]
name = "yukkuri_bevy"
crate-type = ["cdylib"]

[dependencies]
bevy = { version = "0.19.0", default-features = false, features = ["multi_threaded"] }
avian2d = { version = "0.7.0" }
pyo3 = { version = "0.21.0", features = ["extension-module", "hashbrown"] }
serde = { version = "1.0", features = ["derive"] }
toml = "0.8"
rmp-serde = "1.3"
hashbrown = "0.14"
```

### 3.2 FFI Structs Mapped to PyO3
The following structs represent the FFI boundary between Bevy and Python:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

#[pyclass]
#[derive(Clone, Debug)]
pub struct TargetInfo {
    #[pyo3(get, set)]
    pub entity_id: i64,
    #[pyo3(get, set)]
    pub stable_id: i64,
    #[pyo3(get, set)]
    pub type_id: String,
    #[pyo3(get, set)]
    pub growth_stage: String,
    #[pyo3(get, set)]
    pub x: f64,
    #[pyo3(get, set)]
    pub y: f64, // Python coordinate (Y-down)
    #[pyo3(get, set)]
    pub distance: f64,
    #[pyo3(get, set)]
    pub affinity: f64,
    #[pyo3(get, set)]
    pub is_threat: bool,
    #[pyo3(get, set)]
    pub is_prey: bool,
    #[pyo3(get, set)]
    pub is_family: bool,
    #[pyo3(get, set)]
    pub tags: Vec<String>,
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct Blackboard {
    #[pyo3(get, set)]
    pub entity_id: i64,
    #[pyo3(get, set)]
    pub stats: HashMap<String, f64>,
    #[pyo3(get, set)]
    pub x: f64,
    #[pyo3(get, set)]
    pub y: f64, // Python coordinate (Y-down)
    #[pyo3(get, set)]
    pub altitude: f64,
    #[pyo3(get, set)]
    pub flight_state: i32,
    #[pyo3(get, set)]
    pub visible_targets: Vec<TargetInfo>,
    #[pyo3(get, set)]
    pub current_action: String,
    #[pyo3(get, set)]
    pub short_term_memory: HashMap<i64, (f64, f64, f64)>, // Y coordinate is Python (Y-down)
}

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CommandType {
    MOVE_TO,
    FLEE,
    SPEAK,
    PLAY_ANIMATION,
    ATTACK,
    INTERACT,
    MODIFY_STAT,
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct Command {
    #[pyo3(get, set)]
    pub r#type: CommandType,
    #[pyo3(get, set)]
    pub entity_id: i64,
    #[pyo3(get, set)]
    pub payload: Py<PyDict>, // Store dictionary containing variable command arguments
}
```

### 3.3 Y-Axis Coordinate Conversion
- **Rust/Bevy Space (Y-up)**: Origin is typically in the center of the world, Y increases upwards.
- **Python/Pygame Space (Y-down)**: Origin is top-left, Y increases downwards.
- **Conversion Math**:
  $$\text{py\_y} = \text{world\_height} - \text{rust\_y}$$
  $$\text{rust\_y} = \text{world\_height} - \text{py\_y}$$
  This conversion must occur in the Rust code immediately before populating the `Blackboard` (Rust $\to$ Python) and immediately after parsing a returning `Command` (Python $\to$ Rust).

---

## 4. Python BevyWorldAdapter & FFI Entry Point

### 4.1 Mocking Components and Services
The behavior tree actions query components and services from the `World` object. `BevyWorldAdapter` is a custom class that behaves like the esper `World` wrapper.

**`src/yukkuri_game/game/systems/behavior_ffi.py`**:
```python
import py_trees
from typing import Any, TypeVar, cast
from ...engine.components import Transform, LODComponent, Flight, MovementController
from ..components import AIState, Needs, YukkuriStats, Predator, EmotionalState
from ..ai.commands import Command as PyCommand, CommandType as PyCommandType, CommandQueue
from ..ai.behaviors import create_yukkuri_behavior_tree
from ...config import GameConfig

T = TypeVar("T")

class MockConfigSection:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockGameConfig:
    def __init__(self, width: float, height: float):
        self.world = MockConfigSection(width=width, height=height)

class MockServiceLocator:
    def __init__(self, command_queue: CommandQueue, width: float, height: float):
        self._services = {
            CommandQueue: command_queue,
            GameConfig: MockGameConfig(width, height)
        }

    def try_get(self, service_type: type) -> Any:
        return self._services.get(service_type)

class BevyWorldAdapter:
    """Mocks the ECS World interface, feeding data from a Rust Blackboard snapshot."""
    
    def __init__(self, blackboard: Any, ai_state: AIState, world_width: float, world_height: float):
        self.blackboard = blackboard
        self.ai_state = ai_state
        self.queue = CommandQueue()
        self.services = MockServiceLocator(self.queue, world_width, world_height)
        self.time = blackboard.stats.get("game_time", 0.0)

        # Pre-cache visible target indices
        self.targets = {t.entity_id: t for t in blackboard.visible_targets}

    def try_get_component(self, entity_id: int, component_type: type[T]) -> T | None:
        # 1. Component requested is for the ticking entity itself
        if entity_id == self.blackboard.entity_id:
            if component_type is AIState:
                return cast(T, self.ai_state)
            if component_type is Transform:
                return cast(T, Transform(x=self.blackboard.x, y=self.blackboard.y))
            if component_type is Needs:
                return cast(T, Needs(
                    health=self.blackboard.stats.get("health", 100.0),
                    hunger=self.blackboard.stats.get("hunger", 0.0),
                    social=self.blackboard.stats.get("social", 50.0),
                    energy=self.blackboard.stats.get("energy", 100.0),
                    cleanliness=self.blackboard.stats.get("cleanliness", 100.0),
                    bladder=self.blackboard.stats.get("bladder", 0.0),
                    easiness=self.blackboard.stats.get("easiness", 50.0),
                ))
            if component_type is YukkuriStats:
                return cast(T, YukkuriStats(
                    name=self.blackboard.stats.get("name", "Yukkuri"),
                    type_id=self.blackboard.stats.get("type_id", "reimu"),
                    growth_stage="Adult" if self.blackboard.stats.get("is_adult", 1.0) > 0.5 else "Baby"
                ))
            if component_type is MovementController:
                return cast(T, MovementController())
            if component_type is Flight:
                return cast(T, Flight(flight_state=self.blackboard.flight_state))
            if component_type is EmotionalState:
                return cast(T, EmotionalState(
                    happiness=self.blackboard.stats.get("happiness", 0.0),
                    stress=self.blackboard.stats.get("stress", 0.0)
                ))
            return None

        # 2. Component requested is for a visible target entity
        if entity_id in self.targets:
            target = self.targets[entity_id]
            if component_type is Transform:
                return cast(T, Transform(x=target.x, y=target.y))
            if component_type is YukkuriStats:
                return cast(T, YukkuriStats(
                    name=target.type_id,
                    type_id=target.type_id,
                    growth_stage=target.growth_stage
                ))
            if component_type is Needs:
                return cast(T, Needs())
            return None

        return None

    def has_component(self, entity_id: int, component_type: type[Any]) -> bool:
        return self.try_get_component(entity_id, component_type) is not None

    @property
    def commands(self) -> Any:
        # Mock commands buffer
        class MockCommands:
            def remove_component(self, *args, **kwargs):
                pass
        return MockCommands()
```

### 4.2 FFI Entry Point
The module maintains a persistent registry of behavior tree instances and `AIState` components mapping to entity IDs. This prevents garbage collection and maintains behavior tree execution state (e.g., active nodes and tick frequencies) across frames.

```python
# Persistent registries
_trees: dict[int, py_trees.trees.BehaviourTree] = {}
_ai_states: dict[int, AIState] = {}

def tick_entity_with_blackboard(blackboard: Any) -> list[Any]:
    """
    FFI Entry Point. Ticks the behavior tree for the entity based on Rust Blackboard.
    
    Args:
        blackboard: A Rust-passed Blackboard PyO3 object.
        
    Returns:
        list[Command]: List of PyO3 Command objects.
    """
    from yukkuri_bevy import Command, CommandType
    
    entity_id = blackboard.entity_id
    world_width = blackboard.stats.get("world_width", 2000.0)
    world_height = blackboard.stats.get("world_height", 1500.0)

    # 1. Retrieve or create persistent AIState
    if entity_id not in _ai_states:
        _ai_states[entity_id] = AIState()
    ai_state = _ai_states[entity_id]
    ai_state.current_action = blackboard.current_action

    # 2. Create the World Adapter
    adapter = BevyWorldAdapter(blackboard, ai_state, world_width, world_height)

    # 3. Retrieve or create the behavior tree instance
    if entity_id not in _trees:
        root = create_yukkuri_behavior_tree(entity_id, adapter, int(world_width), int(world_height))
        _trees[entity_id] = py_trees.trees.BehaviourTree(root)
        _trees[entity_id].setup(timeout=15)
    tree = _trees[entity_id]

    # 4. Execute tick
    py_trees.blackboard.Blackboard().set("dt", blackboard.stats.get("dt", 0.1))
    tree.tick()

    # 5. Harvest published commands and map to Rust FFI Command objects
    py_commands = adapter.services.try_get(CommandQueue).pop_all()
    rust_commands = []
    for cmd in py_commands:
        # Map python enum value to PyO3 CommandType enum
        rust_cmd_type = getattr(CommandType, cmd.type.name)
        rust_commands.append(Command(
            type=rust_cmd_type,
            entity_id=cmd.entity_id,
            payload=cmd.payload
        ))

    return rust_commands
```

---

## 5. Bevy Game Loop, Tick System & Dispatcher

### 5.1 Bevy AI Tick System (GIL-Safe Exclusive Update)
Because the Python interpreter runs on a single thread and is bound by the GIL, Bevy's AI Tick system must run exclusively on the main thread inside the Bevy `Update` schedule.

```rust
use bevy::prelude::*;
use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Component)]
pub struct YukkuriAgent {
    pub current_action: String,
    pub stats: HashMap<String, f64>,
}

#[derive(Resource)]
pub struct PythonFfiConfig {
    pub world_width: f64,
    pub world_height: f64,
}

/// Ticks AI behaviors for all entities by calling the Python Behavior trees.
pub fn tick_python_ai_system(
    mut commands: Commands,
    config: Res<PythonFfiConfig>,
    query: Query<(Entity, &Transform, &YukkuriAgent)>,
) {
    // Acquire the GIL
    Python::with_gil(|py| {
        // Load the Python FFI entry point module
        let ffi_module = match py.import_bound("yukkuri_game.game.systems.behavior_ffi") {
            Ok(m) => m,
            Err(e) => {
                error!("Failed to import Python FFI module: {:?}", e);
                return;
            }
        };
        let tick_func = match ffi_module.getattr("tick_entity_with_blackboard") {
            Ok(f) => f,
            Err(e) => {
                error!("FFI function not found: {:?}", e);
                return;
            }
        };

        for (entity, transform, agent) in query.iter() {
            // Convert coordinate Y-up to Y-down
            let py_y = config.world_height - transform.translation.y as f64;
            let py_x = transform.translation.x as f64;

            // Pack stats dictionary
            let mut stats = agent.stats.clone();
            stats.insert("world_width".to_string(), config.world_width);
            stats.insert("world_height".to_string(), config.world_height);
            stats.insert("game_time".to_string(), 0.0);
            stats.insert("dt".to_string(), 0.1);

            // Construct Rust Blackboard object
            let blackboard = Blackboard {
                entity_id: entity.index() as i64,
                stats,
                x: py_x,
                y: py_y,
                altitude: transform.translation.z as f64,
                flight_state: 0,
                visible_targets: Vec::new(), // Populated via spatial queries if needed
                current_action: agent.current_action.clone(),
                short_term_memory: HashMap::new(),
            };

            // Convert Blackboard to PyCell/PyObject
            let py_blackboard = match Py::new(py, blackboard) {
                Ok(cell) => cell,
                Err(e) => {
                    error!("Failed to create PyCell: {:?}", e);
                    continue;
                }
            };

            // Call Python FFI
            let py_result = match tick_func.call1((py_blackboard,)) {
                Ok(res) => res,
                Err(e) => {
                    error!("Exception occurred during Python behavior tick: {:?}", e);
                    continue;
                }
            };

            // Extract returning commands
            let rust_commands: Vec<Command> = match py_result.extract() {
                Ok(cmds) => cmds,
                Err(e) => {
                    error!("Failed to extract commands from Python return value: {:?}", e);
                    continue;
                }
            };

            // Dispatch commands to Bevy entity
            for cmd in rust_commands {
                dispatch_ai_command(&mut commands, entity, cmd, &config);
            }
        }
    });
}
```

### 5.2 AI Command Dispatcher
Applies returning FFI commands to the Bevy World. For coordinate-based commands (e.g. `MOVE_TO`), the dispatcher converts the target Y coordinate from Pygame (Y-down) to Bevy (Y-up).

```rust
#[derive(Component)]
pub struct MoveTarget {
    pub x: f32,
    pub y: f32,
    pub acceptance_radius: f32,
}

fn dispatch_ai_command(
    commands: &mut Commands,
    entity: Entity,
    cmd: Command,
    config: &PythonFfiConfig,
) {
    match cmd.r#type {
        CommandType::MOVE_TO => {
            Python::with_gil(|py| {
                let dict = cmd.payload.as_ref(py);
                if let (Ok(x_obj), Ok(y_obj)) = (dict.get_item("target_x"), dict.get_item("target_y")) {
                    if let (Ok(x), Ok(py_y)) = (x_obj.extract::<f32>(), y_obj.extract::<f32>()) {
                        // Apply Y-axis conversion back to Bevy
                        let rust_y = config.world_height as f32 - py_y;
                        
                        commands.entity(entity).insert(MoveTarget {
                            x,
                            y: rust_y,
                            acceptance_radius: dict.get_item("acceptance_radius")
                                .and_then(|o| o.extract::<f32>().ok())
                                .unwrap_or(40.0),
                        });
                    }
                }
            });
        }
        CommandType::SPEAK => {
            // Handle speak (add a text banner/bubble component)
        }
        _ => {
            warn!("Unhandled command type: {:?}", cmd.r#type);
        }
    }
}
```

### 5.3 Avian2d Integration & Schedulers
- **`Update` Schedule (Variable)**: Runs `tick_python_ai_system`.
- **`FixedUpdate` Schedule (Deterministic)**: Runs the Avian2d physics system (`PhysicsPlugins`) and updates positions based on `MoveTarget` velocities.

---

## 6. TOML Archetype Loader

Entities are spawned based on configurations in TOML files. A Bevy resource reads files like `data/archetypes/default.toml` using `serde` and `toml`, attaching colliders and rigid body configurations.

```rust
#[derive(serde::Deserialize, Resource, Debug)]
pub struct ArchetypeDatabase {
    pub archetypes: HashMap<String, ArchetypeConfig>,
}

#[derive(serde::Deserialize, Debug)]
pub struct ArchetypeConfig {
    pub type_id: String,
    pub base_speed: f32,
    pub scale: f32,
    pub collider: ColliderConfig,
}

#[derive(serde::Deserialize, Debug)]
pub enum ColliderShape {
    Circle { radius: f32 },
    Capsule { width: f32, height: f32 },
}

#[derive(serde::Deserialize, Debug)]
pub struct ColliderConfig {
    pub shape: ColliderShape,
    pub density: f32,
    pub friction: f32,
}

/// Spawns an entity using loaded archetype configurations
pub fn spawn_archetype_entity(
    commands: &mut Commands,
    db: &ArchetypeDatabase,
    name: &str,
    position: Vec2,
) {
    if let Some(config) = db.archetypes.get(name) {
        let mut entity_cmds = commands.spawn((
            SpatialBundle::from_transform(Transform::from_xyz(position.x, position.y, 0.0)),
            YukkuriAgent {
                current_action: "Idle".to_string(),
                stats: HashMap::new(),
            },
        ));

        // Attach Avian2d Physics & Collider
        entity_cmds.insert(avian2d::prelude::RigidBody::Dynamic);
        
        match config.collider.shape {
            ColliderShape::Circle { radius } => {
                entity_cmds.insert(avian2d::prelude::Collider::circle(radius * config.scale));
            }
            ColliderShape::Capsule { width, height } => {
                entity_cmds.insert(avian2d::prelude::Collider::capsule(width * config.scale, height * config.scale));
            }
        }
        
        entity_cmds.insert(avian2d::prelude::Friction::new(config.collider.friction));
    }
}
```

---

## 7. Integration Test Design (`tests/migration_test.rs`)

The integration test runs a headless Bevy application, initializing Python, ticking the app, and verifying command output and Y-axis mapping.

```rust
#[cfg(test)]
mod tests {
    use bevy::prelude::*;
    use avian2d::prelude::*;
    use pyo3::prelude::*;
    use std::collections::HashMap;
    use crate::{tick_python_ai_system, PythonFfiConfig, YukkuriAgent, MoveTarget};

    #[test]
    fn test_ffi_command_execution() {
        // Initialize PyO3 Python runtime environment
        pyo3::prepare_freethreaded_python();

        // 1. Setup Bevy App
        let mut app = App::new();
        app.add_plugins(MinimalPlugins);
        app.add_plugins(PhysicsPlugins::default());
        
        // Add resources
        app.insert_resource(PythonFfiConfig {
            world_width: 1000.0,
            world_height: 800.0,
        });

        // 2. Spawn a test entity
        let mut stats = HashMap::new();
        stats.insert("hunger".to_string(), 85.0); // High hunger triggers forage/eat
        stats.insert("energy".to_string(), 90.0);
        
        let entity_id = app.world_mut().spawn((
            Transform::from_xyz(100.0, 100.0, 0.0), // Rust coordinate (Y=100) -> Python Y = 800 - 100 = 700
            YukkuriAgent {
                current_action: "Wander".to_string(),
                stats,
            },
        )).id();

        // 3. Register FFI tick system
        app.add_systems(Update, tick_python_ai_system);

        // 4. Update Bevy App (Ticking FFI)
        app.update();

        // 5. Verify the results
        // Behavior trees should have yielded a command such as MOVE_TO, which
        // is captured by the dispatcher and translates to a MoveTarget component.
        let move_target = app.world().get::<MoveTarget>(entity_id);
        assert!(move_target.is_some(), "MOVE_TO command was not dispatched as a component");
        
        let target = move_target.unwrap();
        // Target coordinates in Pygame should be converted correctly to Bevy space
        assert!(target.x >= 0.0 && target.x <= 1000.0);
        assert!(target.y >= 0.0 && target.y <= 800.0);
    }
}
```
