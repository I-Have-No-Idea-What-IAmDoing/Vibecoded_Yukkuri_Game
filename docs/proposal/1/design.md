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
- **System Decoupling**: For critical, high-frequency interactions, prefer explicitly defined interfaces or callbacks (e.g., C#-style Delegates or Signals) rather than hard system-to-system dependencies. This maintains decoupling while avoiding global event bus overhead.

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

We adopt a decoupled, snapshot-based persistence model that enforces strict separation between Data, Logic, and Serialization. This revision addresses concerns regarding boilerplate, pollution, and fragility, and now explicitly handles dynamic world state and entity references.

#### 7.1. Core Principles

- **No Global Session in ECS**: Systems operate on Components. Persistence is an infrastructure concern handled by the `SceneManager`.
- **POPOs & Dataclasses**: Components are standard Python `dataclasses`. They contain **no** serialization logic and **no** migration logic.
- **Key Constants**: To avoid "stringly typed" errors, persistence keys for global state are defined as `Final` constants.

#### 7.2. Global State Injection (The "Context" Layer)

For singleton data (Player Inventory, Quest State) that persists *across* scenes:

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
    The `SceneManager` resolves these dependencies, migrating data if necessary, and injects them into the `SceneContext`.

3.  **Setup Injection**:
    ```python
    def setup(self, world, context: SceneContext):
        # Injected data is ready to use
        inv = context.data[keys.player.INVENTORY]
        player = world.create_entity(inv, ...)
    ```

#### 7.3. Dynamic World Persistence (The "Level" Layer)

For saving the state of a specific level (e.g., 50 enemies, dropped items):

- **WorldSerializer**: A dedicated subsystem that iterates over all entities with a `Persistable` component.
- **Dynamic Collections**: Unlike `INJECTIONS` (which map 1:1), `WorldSerializer` saves a list of entities.
- **Entity ID Remapping**:
    - **Stable IDs**: Persistent entities are assigned a stable ID. This can be a UUID (universally unique) or a simple monotonically increasing integer managed by the Scene, depending on complexity requirements.
    - **Reference Handling**: When deserializing, a two-pass approach is used.
        1.  **Create Entities**: Instantiate all entities and map their `SavedID` to the new runtime `EntityID`.
        2.  **Resolve References**: Components that reference other entities (e.g., `Owner(target_id)`) use the map to update `target_id` to the correct runtime ID.

#### 7.4. Decoupled Schema Migration & Versioning

To prevent "Migration Pollution" in component classes, migration logic is housed in separate Strategy classes.

- **Versioning**: Components define a `_version_ = N` field.
- **Migration Registry**: We register migration functions that transform raw dictionaries.
- **Migration Semantics**:
    - **Additive Changes**: Handled by default values.
    - **Breaking Changes**: Require a registered migration function.
    - **Ordering**: Migrations are applied sequentially.

```python
MigrationRegistry.register(Inventory, from_version=1, to_version=2, func=migrate_v1_to_v2)
```

#### 7.5. Persistence Strategy: Snapshotting

- **Snapshotting**: Data is serialized only at specific lifecycle events (Transition, Checkpoint).
- **Atomicity**: Snapshots are "all-or-nothing" with atomic file writes.
- **Concurrency**: Data collection happens on the Main Thread; I/O is Async.

#### 7.6. Benefits

- **Complete Persistence**: Handles both Global State (Player) and Dynamic Level State (Enemies).
- **Referential Integrity**: Entity relationships are preserved across save/load.
- **Zero Boilerplate**: No manual `deserialize()` calls in scene code for injected dependencies.
- **Clean Architecture**: Components remain pure data.

## Architecture Diagram (Conceptual)

```
[Application]
  |
  +-- [ServiceContainer]
  |
  +-- [SceneManager]
       |
       +-- [Hydration Layer] (Deserializes Global State)
       |
       +-- [Active Scene]
            |
            +-- [WorldSerializer] (Handles Dynamic Entities & ID Remapping)
            |
            +-- [ECS World]
                 |
                 +-- [Entities] (ID + Components)
                 |
                 +-- [Systems] (Logic)
```
