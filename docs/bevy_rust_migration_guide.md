# Blueprint: Pygame-CE to Bevy & Rust Migration Guide

This guide provides a comprehensive technical blueprint and integration specification for porting the *Yukkuri Raising Game* engine to Rust and Bevy, using Python as the embedded scripting host via PyO3.

---

## 1. Hybrid Engine Architecture

In the target architecture, Rust runs as the high-performance host executing the game loop, physics simulation (XPBD), spatial indexes, and rendering. The Python runtime is embedded inside the Bevy executable, acting as a scripting sandbox for the AI Behavior Trees.

```mermaid
graph TD
    subgraph Rust Host (Bevy Engine)
        App[Bevy App] -->|Ticks| PS[Physics System XPBD]
        App -->|Query Neighbors| SH[Spatial Hashing]
        App -->|1. Build Snapshots| PyBridge[PyO3 FFI Bridge]
        PyBridge -->|2. Tick Trees| PyAI[Embedded Python AI]
        PyAI -->|3. Return Commands| PyBridge
        PyBridge -->|4. Dispatch Actions| MS[Movement & Gameplay Systems]
    end
```

---

## 2. PyO3 FFI Boundary Specifications

### A. Read-Only Perception Snapshot (`Blackboard`)
Every frame, Bevy's AI manager queries spatial hashes and component states to build localized read-only snapshots. These are converted to Python objects and passed to the Behavior Trees.

#### Rust Struct Equivalents (`src/ai/blackboard.rs`)
```rust
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

#[pyclass]
#[derive(Clone, Debug)]
pub struct TargetInfo {
    #[pyo3(get)]
    pub entity_id: u32,
    #[pyo3(get)]
    pub stable_id: u64,
    #[pyo3(get)]
    pub type_id: String,
    #[pyo3(get)]
    pub growth_stage: String,
    #[pyo3(get)]
    pub x: f32,
    #[pyo3(get)]
    pub y: f32,
    #[pyo3(get)]
    pub distance: f32,
    #[pyo3(get)]
    pub affinity: f32,
    #[pyo3(get)]
    pub is_threat: bool,
    #[pyo3(get)]
    pub is_prey: bool,
    #[pyo3(get)]
    pub is_family: bool,
    #[pyo3(get)]
    pub tags: HashSet<String>,
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct Blackboard {
    #[pyo3(get)]
    pub entity_id: u32,
    #[pyo3(get)]
    pub stats: HashMap<String, f32>,
    #[pyo3(get)]
    pub x: f32,
    #[pyo3(get)]
    pub y: f32,
    #[pyo3(get)]
    pub altitude: f32,
    #[pyo3(get)]
    pub flight_state: u32,
    #[pyo3(get)]
    pub visible_targets: Vec<TargetInfo>,
    #[pyo3(get)]
    pub current_action: String,
    #[pyo3(get)]
    pub short_term_memory: HashMap<u32, (f32, f32, f32)>,
}
```

---

### B. Write Intentions (`CommandQueue`)
The Python AI ticks over the blackboard and pushes high-level intentions into `CommandQueue`. At the end of the Python tick, Bevy pops all packets and dispatches them in Rust.

#### Rust Struct Equivalents (`src/ai/commands.rs`)
```rust
use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommandType {
    MoveTo,
    Flee,
    Speak,
    PlayAnimation,
    Attack,
    Interact,
    ModifyStat,
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct Command {
    #[pyo3(get)]
    pub cmd_type: CommandType,
    #[pyo3(get)]
    pub entity_id: u32,
    #[pyo3(get)]
    pub payload: HashMap<String, String>, // Serialized parameters (e.g. target_x -> string float)
}

#[pymethods]
impl Command {
    #[new]
    pub fn new(cmd_type: CommandType, entity_id: u32, payload: HashMap<String, String>) -> Self {
        Self { cmd_type, entity_id, payload }
    }
}
```

---

### C. The FFI Execution Loop (Rust Side)
Here is the concrete PyO3 implementation to embed the Python runtime, load the AI behavior modules, tick the trees with read-only Blackboard structs, and extract the returned commands.

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule;
use crate::ai::blackboard::Blackboard;
use crate::ai::commands::Command;

pub struct PythonAISandbox {
    behavior_module: Py<PyModule>,
}

impl PythonAISandbox {
    pub fn new(py: Python) -> PyResult<Self> {
        // Load the Python behavior system entrypoint
        let sys = py.import_bound("sys")?;
        let path: &Bound<'_, pyo3::types::PyList> = sys.getattr("path")?.downcast()?;
        path.insert(0, "./src")?; // Ensure gameplay scripts are in import search path
        
        let behavior_module = py.import_bound("yukkuri_game.game.systems.behavior")?
            .unbind();
            
        Ok(Self { behavior_module })
    }

    pub fn tick_entity(
        &self,
        py: Python,
        blackboard: Blackboard,
    ) -> PyResult<Vec<Command>> {
        // Call Python tick function: tick_entity_with_blackboard(blackboard)
        let behavior_module = self.behavior_module.bind(py);
        let result = behavior_module
            .call_method1("tick_entity_with_blackboard", (blackboard,))?;
            
        // Extract Vec<Command> directly from returned Python list
        let commands: Vec<Command> = result.extract()?;
        Ok(commands)
    }
}
```

---

## 3. Bevy & Avian 2D Physics Dispatcher Mapping

When Bevy pops Python AI commands, it maps them directly to Avian 2D (XPBD) component mutations and impulses inside a standard Bevy system.

```rust
use bevy::prelude::*;
use avian2d::prelude::*;
use std::collections::HashMap;
use crate::ai::commands::{Command, CommandType};

// Components
#[derive(Component)]
pub struct MoveTarget {
    pub position: Vec2,
    pub acceptance_radius: f32,
}

#[derive(Component)]
pub struct Needs {
    pub hunger: f32,
    pub energy: f32,
    pub health: f32,
}

// Bevy System to execute popped commands
pub fn apply_ai_commands(
    mut commands: Commands,
    popped_commands: Res<Vec<Command>>, // Resource storing current frame's popped commands
    mut query: Query<(Entity, &mut LinearVelocity, &mut Needs, &Transform)>,
) {
    for cmd in popped_commands.iter() {
        // Convert Python FFI entity_id to Bevy Entity
        let bevy_entity = Entity::from_raw(cmd.entity_id);
        
        if let Ok((entity, mut velocity, mut needs, transform)) = query.get_mut(bevy_entity) {
            match cmd.cmd_type {
                CommandType.Flee => {
                    let vx = cmd.payload.get("velocity_x")
                        .and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                    let vy = cmd.payload.get("velocity_y")
                        .and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                        
                    // Mutate rigid body velocity directly
                    velocity.0 = Vec2::new(vx, vy);
                }
                CommandType.MoveTo => {
                    let tx = cmd.payload.get("target_x")
                        .and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                    let ty = cmd.payload.get("target_y")
                        .and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                    let accept = cmd.payload.get("acceptance_radius")
                        .and_then(|v| v.parse::<f32>().ok()).unwrap_or(25.0);
                        
                    // Attach movement destination for navigation system
                    commands.entity(entity).insert(MoveTarget {
                        position: Vec2::new(tx, ty),
                        acceptance_radius: accept,
                    });
                }
                CommandType.ModifyStat => {
                    let stat_name = cmd.payload.get("stat_name").cloned().unwrap_or_default();
                    let amount = cmd.payload.get("amount")
                        .and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                        
                    match stat_name.as_str() {
                        "hunger" => needs.hunger = (needs.hunger + amount).clamp(0.0, 100.0),
                        "energy" => needs.energy = (needs.energy + amount).clamp(0.0, 100.0),
                        "health" => needs.health = (needs.health + amount).clamp(0.0, 100.0),
                        _ => {}
                    }
                }
                _ => {}
            }
        }
    }
}
```

---

## 4. Data-Driven TOML Archetype Loading

Instead of code-defined constants, Bevy dynamically loads Yukkuri prefabs at startup.

### A. Example Archetype Config (`data/prefabs/reimu.toml`)
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

### B. Rust Prefab Loader (`src/prefabs/loader.rs`)
```rust
use bevy::prelude::*;
use serde::Deserialize;

#[derive(Deserialize, Asset, TypePath)]
pub struct YukkuriPrefab {
    pub prefab: PrefabHeader,
    pub physics: PhysicsPrefab,
    pub needs: NeedsPrefab,
    pub steering: SteeringPrefab,
}

#[derive(Deserialize)]
pub struct PrefabHeader {
    pub type_id: String,
    pub name: String,
    pub growth_stage: String,
}

// Spawns Bevy Entity with Avian components mapped from TOML
pub fn spawn_yukkuri_prefab(
    commands: &mut Commands,
    prefab: &YukkuriPrefab,
    position: Vec2,
) {
    commands.spawn((
        SpatialBundle::from_transform(Transform::from_xyz(position.x, position.y, 0.0)),
        avian2d::prelude::RigidBody::Dynamic,
        avian2d::prelude::Collider::circle(prefab.physics.radius),
        avian2d::prelude::Mass(prefab.physics.mass),
        avian2d::prelude::Friction::new(prefab.physics.friction),
        // Add stats & gameplay state components...
    ));
}
```

---

## 5. State Persistence Specs (SQLite & MsgPack)

To maintain optimal save speeds and binary safety:
1. **Static World & Coordinates**: Saved into a relational SQLite schema (position, stable ID, archetype name).
2. **Dynamic Scripting State**: Dynamic stats, needs, and memory blobs are serialized on the Python side, returned as a compact binary block (`MsgPack`), and stored in a single SQLite `BLOB` column per entity.

### A. Python Serialization Hook
```python
import msgpack
from typing import Any

def serialize_dynamic_state(needs_comp: Any, ai_state_comp: Any) -> bytes:
    """Serializes mutable stats and script memory using MessagePack.
    
    Args:
        needs_comp: The Needs component instance.
        ai_state_comp: The AIState component instance.
        
    Returns:
        bytes: Compressed binary data block.
    """
    state_dict = {
        "energy": float(needs_comp.energy),
        "hunger": float(needs_comp.hunger),
        "health": float(needs_comp.health),
        "stress": float(needs_comp.stress) if hasattr(needs_comp, "stress") else 0.0,
        "memory": ai_state_comp.state_data if ai_state_comp.state_data else {}
    }
    return msgpack.packb(state_dict, use_bin_type=True)
```

### B. Rust Deserialization Hook
```rust
use rmp_serde::from_slice;
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize, Debug)]
pub struct DynamicAIState {
    pub energy: f32,
    pub hunger: f32,
    pub health: f32,
    pub stress: f32,
    pub memory: HashMap<String, serde_json::Value>, // Handles dynamic python memory maps
}

pub fn load_dynamic_state_to_entity(
    blob_bytes: &[u8],
) -> Result<DynamicAIState, rmp_serde::decode::Error> {
    // Unpack MessagePack binary directly into Rust struct
    let state: DynamicAIState = from_slice(blob_bytes)?;
    Ok(state)
}
```

---

## 6. Bevy World Serialization & Reflection (Bevy 0.19+)

In Bevy 0.19, the old scene serialization crate has been renamed to `bevy_world_serialization` (with the `bevy_scene` name now representing the Next Generation Scene system). This guide outlines how to use `bevy_world_serialization` (formerly `bevy_scene`) and `bevy_reflect` to automate save-state component serialization and structural prefab templating.

### A. Component Reflection Registration
Any component that needs to be serialized via Bevy Worlds must be registered in the Type Registry:

```rust
use bevy::prelude::*;

#[derive(Component, Reflect, Default)]
#[reflect(Component)]
pub struct Needs {
    pub hunger: f32,
    pub energy: f32,
    pub health: f32,
}

#[derive(Component, Reflect, Default)]
#[reflect(Component)]
pub struct Persistable; // Save target marker component

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .register_type::<Needs>()
        .register_type::<Persistable>()
        .register_type::<Transform>()
        .run();
}
```

### B. Dynamic World Building (Saves/Loads)
To save the game, Bevy queries all entities marked with `Persistable` and builds a dynamic world containing only their reflected, registered components. 

> [!NOTE]
> In Bevy 0.19, `DynamicSceneBuilder` is renamed to `DynamicWorldBuilder`, `DynamicScene` is renamed to `DynamicWorld`, and `from_world` now requires a reference to the `TypeRegistry`:

```rust
use bevy::prelude::*;
use bevy::world_serialization::{DynamicWorldBuilder, DynamicWorldRoot};
use bevy::tasks::IoTaskPool;
use std::fs::File;
use std::io::Write;

pub fn save_game_system(world: &mut World) {
    let type_registry = world.resource::<AppTypeRegistry>().clone();
    let registry_read = type_registry.read();
    
    // Create the builder, passing the registry read lock
    let mut builder = DynamicWorldBuilder::from_world(world, &registry_read);

    // Query all persistable entities
    let mut query = world.query_filtered::<Entity, With<Persistable>>();
    let persistable_entities: Vec<Entity> = query.iter(world).collect();

    // Extract reflected components
    builder.extract_entities(persistable_entities.into_iter());
    let dynamic_world = builder.build();

    // Serialize to RON format
    let ron_string = dynamic_world.serialize_ron(&registry_read)
        .expect("Failed to serialize save state");

    // Write file asynchronously
    IoTaskPool::get().spawn(async move {
        File::create("saves/quicksave.scn.ron")
            .and_then(|mut file| file.write_all(ron_string.as_bytes()))
            .expect("Failed to write save file");
    }).detach();
}
```

### C. Integrating Python Scripting States in Worlds
To save dynamic Python memory (`AIState.state_data`) inside reflected Bevy dynamic worlds, wrap the MsgPack binary blob in a reflected component on the entity:

```rust
#[derive(Component, Reflect, Default)]
#[reflect(Component)]
pub struct PythonState {
    pub serialized_blob: Vec<u8>, // messagepack compressed bytes
}
```
Bevy's world serializer will write this binary vector directly to the save file as standard text-encoded bytes, allowing seamless loading and unloading back into Python via PyO3.

### D. Structural Prefabs & Dynamic Templating
Instead of procedurally spawning entity hierarchies, use Bevy dynamic world assets (`.scn.ron`) as templates, spawning them and insertion-overlaying archetype properties dynamically:

```rust
use bevy::prelude::*;
use bevy::world_serialization::WorldAssetRoot;

pub fn spawn_templated_yukkuri(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    reimu_toml_prefab: Res<YukkuriPrefab>, // Config loaded from TOML
) {
    // 1. Spawn structural template layout using WorldAssetRoot (renamed from SceneRoot)
    commands.spawn(WorldAssetRoot(asset_server.load("scenes/yukkuri_base.scn.ron")))
    // 2. Overlay archetype physics & stats components
    .insert((
        Needs {
            hunger: reimu_toml_prefab.needs.hunger,
            energy: reimu_toml_prefab.needs.energy,
            health: reimu_toml_prefab.needs.max_health,
        },
        avian2d::prelude::RigidBody::Dynamic,
        avian2d::prelude::Collider::circle(reimu_toml_prefab.physics.radius),
    ));
}
```

---

## 7. Critical Porting Considerations & Gotchas

When porting a game from Pygame-CE to Bevy and Rust, three major architectural gotchas must be noted and handled:

### A. Y-Axis Coordinate Inversion (Pygame Y-down vs. Bevy Y-up)
- **Problem**: In Pygame, the origin `(0,0)` is at the top-left corner, and the Y-axis points **downwards**. In Bevy (and modern 3D rendering engines), the standard Cartesian coordinate system is used, where the Y-axis points **upwards**.
- **Solution**: The FFI bridge must perform automatic coordinate translation. Whenever Bevy populates the `Blackboard` snapshot, it should map the Y coordinates:
  $$\text{Python } y = \text{World Height} - \text{Bevy } y$$
  Similarly, when Bevy reads target coordinates from Python `MOVE_TO` commands, it must apply the reverse transformation to maintain physical accuracy:
  $$\text{Bevy } y = \text{World Height} - \text{Python } y$$

### B. PyO3 Thread Binding & The Python GIL
- **Problem**: Bevy is a massively parallel engine; it runs ECS systems across multiple CPU threads concurrently. However, the Python C API (via PyO3) is strictly thread-bound due to the **Global Interpreter Lock (GIL)**. If multiple Bevy systems try to acquire the Python GIL concurrently, they will dead-lock or panic, crashing the executable.
- **Solution**: The Python AI system in Bevy must run as a **single-threaded, exclusive system** using Bevy’s `NonSend` resource markers, or run sequentially on a single thread. Avoid ticking Python AI in parallel systems. Use a centralized Bevy system that acquires the GIL once per frame, ticks all active behavior trees, and returns the command packets in a single sequential pass:
  ```rust
  // Mark the sandbox as NonSend so Bevy strictly schedules it on the main thread
  pub fn tick_python_ai_system(
      mut commands: Commands,
      sandbox: NonSend<PythonAISandbox>,
      mut query: Query<(Entity, &mut Needs, &Transform)>,
  ) {
      Python::with_gil(|py| {
          for (entity, needs, transform) in query.iter_mut() {
              // 1. Construct Blackboard struct
              // 2. call sandbox.tick_entity(py, blackboard)
              // 3. Queue returned Command packets...
          }
      });
  }
  ```

### C. Fixed vs. Variable Ticking (Avian XPBD Physics vs. Behavior Trees)
- **Problem**: Avian 2D (XPBD) performs physical constraints calculations inside a **fixed time-step loop** (e.g., exactly 60Hz via `Time<Fixed>`), whereas gameplay scripting and standard systems run inside a **variable time-step loop** (e.g., variable rendering FPS via `Time<Virtual>`). Ticking heavy AI behavior trees inside `Time<Fixed>` will cause massive frame-time spikes (stuttering).
- **Solution**: Ticking Behavior Trees should run in the variable update schedule (e.g. `Update` system set) and use round-robin batch scheduling (which we implemented in `BehaviorSystem.update()` with the queue) to distribute ticking workloads smoothly across multiple frames. High-level commands popped from Python are stored as Bevy ECS components (like `MoveTarget`) and carried over into the fixed physics update schedule sequentially.


