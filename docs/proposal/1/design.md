# Architecture Redesign Proposal

## Overview

This proposal outlines a refined architecture for the Yukkuri Game Engine. The goal is to enhance modularity, scalability, and maintainability while adopting pragmatic design principles that balance structure with developer ergonomics.

## Core Components

### 1. Application Lifecycle & Scene Management

The current `GameManager` handles too many responsibilities. We propose splitting it into an `Application` class and a `SceneManager`.

- **Application**: Responsible for initializing the engine, the main loop, and window management. It owns the `SceneManager`.
- **SceneManager**: Manages a stack of `Scene` objects. It handles transitions (push, pop, replace).
- **Scene**: A container for a specific game state (e.g., `MainMenuScene`, `GameplayScene`). Each Scene owns its own ECS World and specific Systems.

### 2. Phase-Based Event System

To avoid "call stack explosion" without adding the complexity/non-determinism of a fully asynchronous queue:

- **Phase-Based Dispatch**: Events are processed at specific points in the frame (e.g., `PreUpdate`, `PostUpdate`).
- **Typed Events**: Enforce strict typing for event data to aid debugging and IDE support.
- **Direct Observers**: For critical, high-frequency interactions (e.g., collision), prefer direct system-to-system communication or direct callback registration over the global event bus.

### 3. Context-Aware Input System

The Input system must handle different states (Menu vs Gameplay).

- **ActionMapper**: Maps raw inputs to logical Actions (`JUMP`, `CONFIRM`).
- **Input Contexts**: Defines *active* sets of mappings. (e.g., The `UI_Context` maps `Esc` to `Close Menu`, while `Gameplay_Context` maps `Esc` to `Pause`).
- **Priority**: Contexts can consume inputs, preventing "shoot" actions while clicking a menu button.

### 4. Pythonic Prefabs (Not YAML)

We reject the use of YAML/TOML for prefabs. Python *is* the best configuration language.

- **Implementation**: A `prefabs/` directory containing Python modules.
- **Definition**: Functions or classes that return fully configured Entities.
  ```python
  def create_baby_yukkuri(x, y):
      e = Entity()
      e.add(Transform(x, y))
      e.add(AI(behavior="cry"))
      return e
  ```

### 5. Pragmatic ECS

We will stick to ECS principles but relax dogmatic restrictions:

- **Components**: Primarily data, but **Helper Methods are allowed** (e.g., `health_component.is_dead()`, `velocity.add_impulse()`) to encapsulate local data transformations.
- **Systems**: Handle cross-component logic and interactions.
- **State**: Systems may cache query results or time-deltas for performance, but "Game State" remains in components or the Scene Context.

### 6. Service Access

A lightweight **ServiceContainer** will provide access to cross-cutting concerns (Audio, Logging, Assets).

- **Explicit Registration**: Services are registered at startup.
- **Facade**: The container acts as a facade, but systems should ideally take dependencies via `__init__` where feasible to improve testability.

### 7. Data Persistence & State Transfer

We adopt a decoupled, snapshot-based persistence model that enforces strict separation between Data, Logic, and Serialization. This revision addresses concerns regarding boilerplate, pollution, and fragility.

#### 7.1. Core Principles

- **No Global Session in ECS**: Systems operate on Components. Persistence is an infrastructure concern handled by the `SceneManager`.
- **POPOs & Dataclasses**: Components are standard Python `dataclasses`. They contain **no** serialization logic and **no** migration logic.
- **Key Constants**: To avoid "stringly typed" errors, persistence keys are defined as `Final` constants in designated `keys` modules (e.g., `keys.player.INVENTORY`), not as raw string literals.

#### 7.2. Automated Lifecycle (The "No Boilerplate" Rule)

Instead of manual fetching and deserialization inside `setup`, the engine handles hydration *before* the Scene initializes.

1.  **Scene Manifest**:
    The Scene declares its requirements using a typed mapping.
    ```python
    class DungeonScene(Scene):
        # Maps a Persistence Key to a Component Type
        INJECTIONS = {
            keys.player.INVENTORY: Inventory,
            keys.player.STATS: Stats
        }
    ```

2.  **Auto-Hydration**:
    The `SceneManager` resolves these dependencies. It loads the raw data, runs necessary migrations (see 7.3), deserializes it into the target Component classes, and bundles them into a `Context`.

3.  **Setup Injection**:
    The `setup` method receives these ready-to-use objects.
    ```python
    def setup(self, world, context: SceneContext):
        # context.data is a dict-like object strictly typed by INJECTIONS
        # No manual deserialization needed.
        inv = context.data[keys.player.INVENTORY]
        player = world.create_entity(inv, ...)
    ```

#### 7.3. Decoupled Schema Migration

To prevent "Migration Pollution" in component classes, migration logic is housed in separate Strategy classes.

- **Versioning**: Components define a simple `_version_ = N` field.
- **Migration Registry**: We register migration functions that transform raw dictionaries.

```python
# In migrations/inventory.py
def migrate_v1_to_v2(data: dict) -> dict:
    data['items'] = convert_list_to_slots(data['items'])
    return data

# Registration (at startup)
MigrationRegistry.register(Inventory, from_version=1, to_version=2, func=migrate_v1_to_v2)
```

The deserializer automatically applies the chain of migrations (v1 -> v2 -> v3) before converting the dict to the Dataclass.

#### 7.4. Persistence Strategy: Snapshotting

We explicitly reject "Dirty Checking" proxies due to their complexity and overhead.

- **Snapshotting**: Data is serialized only at specific lifecycle events:
    - **Scene Transition**: When leaving a scene.
    - **Checkpoints**: Explicit calls (e.g., Save Points).
    - **Background Autosave**: A background task triggers a snapshot of `Persistable` components every N minutes to mitigate crash data loss.
- **Explicit Persistence**: Only entities/components marked with a `Persistable` tag (or registered in a `Scene.EXPORTS` list) are saved. This eliminates ambiguity about "what is relevant".

#### 7.5. Benefits

- **Zero Boilerplate**: No manual `deserialize()` calls in scene code.
- **Clean Architecture**: Components remain pure data; migrations are separate.
- **Type Safety**: Keys are constants, and migrations are registered against Types.
- **Predictability**: Snapshotting is deterministic, unlike magic proxy wrappers.

## Architecture Diagram (Conceptual)

```
[Application]
  |
  +-- [ServiceContainer] (Audio, Input, Resources, Session)
  |
  +-- [SceneManager]
       |
       +-- [Hydration Layer] (Deserializes & Migrates Data)
       |
       +-- [Active Scene]
            |
            +-- [ECS World]
                 |
                 +-- [Entities] (ID + Components)
                 |
                 +-- [Systems] (Logic)
```
