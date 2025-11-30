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

To ensure robustness, maintainability, and forward compatibility, we propose a decoupled persistence model that relies on standard Python features and explicit versioning.

#### 7.1. Core Principles

- **No Global Session in ECS**: Systems inside a Scene **never** access a global `GameSession` directly.
- **POPOs & Dataclasses**: Components are standard Python `dataclasses` or Plain Old Python Objects. We do **not** inherit from library-specific classes (like `msgspec.Struct`). The serialization layer handles the conversion transparently.
- **Scoped Keys**: Data keys are namespaced strings (e.g., `"player.inventory"`, `"world.dungeon.flags"`) rather than a monolithic global Enum. This allows modular development without central bottlenecks.

#### 7.2. The Lifecycle

1.  **Scene Manifest (Contract)**
    - Each Scene declares its data dependencies using namespaced keys.
    - **Example**:
      ```python
      class DungeonScene(Scene):
          MANIFEST = {
              "required": ["player.inventory", "player.stats"],
              "optional": ["dungeon.flags"]
          }
      ```

2.  **Hydration (Inject with Versioning)**
    - The `SessionManager` retrieves data. Each data blob includes a `_version` field.
    - **Schema Evolution**: Before injection, the data is passed through a migration pipeline if the stored version is older than the current component version.
    - The data is then decoded into the Component dataclass.
      ```python
      # Scene Setup
      def setup(self, world, initial_state):
          player = world.create_entity()
          # Migration and Decoding happen here
          inv_data = initial_state.get("player.inventory")
          inv = self.serializer.deserialize(inv_data, target_type=Inventory)
          player.add(inv)
      ```

3.  **Gameplay & Automated Tracking**
    - **No Manual Dirty Flags**: We avoid manual `is_dirty` flags which are error-prone.
    - **Strategy**:
        - *Option A (Preferred)*: Use a `SaveState` system that snapshots critical data at meaningful moments (Checkpoints, Level Transitions, Exit).
        - *Option B (Optimization)*: If incremental saving is strictly required, use a proxy wrapper or `__setattr__` hook *only* on the `Session` object or specific `ObservedComponents` to track changes automatically, ensuring developers cannot "forget" to flag a change.

4.  **Commit (Persist)**
    - The `PersistenceSystem` gathers data from relevant components.
    - It attaches the current `_schema_version` to the data.
    - The `SessionManager` saves this structured data (e.g., via `msgspec`, `pickle`, or `json` - the format is an implementation detail hidden from the game logic).

#### 7.3. Schema Migration Strategy

To support updates and patches, all persistable components must define a version and a migration hook.

```python
@dataclass
class Inventory:
    items: list[str]
    version: int = 2

    @staticmethod
    def migrate(data: dict, old_version: int) -> dict:
        if old_version < 2:
            # Convert old list format to new format
            data['items'] = convert_items(data['items'])
        return data
```

#### 7.4. Benefits

- **Vendor Neutrality**: Components are just Python classes. We can switch serialization libraries (JSON, MsgPack, Pickle) without touching game logic.
- **Safety**: Automated tracking or explicit snapshots prevents "forgot to save" bugs.
- **Longevity**: Built-in versioning ensures save files from v1.0 still work in v2.0.
- **Scalability**: Namespaced keys allow multiple developers to work on different game modules without conflicting in a central file.

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
