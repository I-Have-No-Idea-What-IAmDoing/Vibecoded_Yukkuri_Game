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

To avoid the pitfalls of shared mutable global state while solving the performance and boilerplate issues of strict DTOs, we will adopt a **Manifest & Protocol** model.

#### 7.1. Core Principles

- **No Global Session in ECS**: Systems inside a Scene **never** access a global `GameSession` directly.
- **Serializable Protocol**: Instead of separate DTO classes, Components that require persistence must implement a `Serializable` protocol (e.g., `to_dict()` and `from_dict()`). This eliminates duplicate class definitions.
- **Explicit Contracts (Manifests)**: Scenes must declare exactly what data they require from the session. This prevents the "God Object" problem where a SceneManager has to know the internals of every Scene.

#### 7.2. The Lifecycle

1.  **Scene Manifest (Contract)**
    - Each Scene class defines a static `Manifest` describing its data dependencies.
    - **Example**:
      ```python
      class DungeonScene(Scene):
          MANIFEST = {
              "required": ["player_inventory", "player_stats"],
              "optional": ["dungeon_flags"]
          }
      ```

2.  **Hydration (Inject)**
    - When the `SceneManager` pushes a new Scene, it consults the `MANIFEST`.
    - It fetches the requested keys from the `SessionStore`.
    - It injects this data into the Scene as a raw dictionary (`initial_state`).
    - The Scene's `setup()` method uses component `from_dict()` methods to populate the ECS.
      ```python
      def setup(self, world, initial_state):
          player = world.create_entity()
          player.add(Inventory.from_dict(initial_state["player_inventory"]))
      ```

3.  **Gameplay & Incremental Tracking**
    - Systems modify Components normally.
    - To avoid "Stop-the-World" serialization spikes, we introduce **Dirty Flags**.
    - When a relevant component changes (e.g., item added), it marks itself as `dirty`.

4.  **Commit (Persist)**
    - On checkpoint or transition, the `PersistenceSystem` queries **only** components marked as `dirty`.
    - It calls `to_dict()` on them and bundles the changes.
    - This delta is sent to the `SessionManager`, which upserts the data into the persistent store.
    - **Example**:
      ```python
      # PersistenceSystem
      updates = {}
      for entity, (inv,) in world.get_components(Inventory):
          if inv.is_dirty:
              updates["player_inventory"] = inv.to_dict()
              inv.clean() # Reset flag
      scene_manager.commit_changes(updates)
      ```

#### 7.3. Benefits

- **Zero Boilerplate**: No need to maintain parallel `InventoryDTO` classes. The Component is the definition.
- **Performance**: We only serialize what changed. An autosave in a massive world is cheap if only one chest was opened.
- **Decoupling**: The `SceneManager` is generic; it simply fulfills the `MANIFEST` contract without knowing what the data means.

## Architecture Diagram (Conceptual)

```
[Application]
  |
  +-- [ServiceContainer] (Audio, Input, Resources, Session)
  |
  +-- [SceneManager]
       |
       +-- [Active Scene]
            |
            +-- [ECS World]
                 |
                 +-- [Entities] (ID + Components)
                 |
                 +-- [Systems] (Logic)
```
