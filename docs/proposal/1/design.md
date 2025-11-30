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

### 7. Data Persistence & State Management

To address the complexity of state management, we distinguish between **Global Session State** (Data that persists across the entire game, e.g., Inventory, Quest Flags) and **Local World State** (Data specific to a scene instance, e.g., Enemy positions, dropped items).

#### 7.1. Global Session State (Manifest & Protocol)

- **Purpose**: Managing data that must survive Scene transitions.
- **Mechanism**: The `SessionManager` holds the "Truth". Scenes request access via a `Manifest`.
- **Versioning**: Components inheriting from `msgspec.Struct` must include a `_version` field. The Persistence layer includes a **Migration Registry** to transform old data schemas to new ones during load, decoupling runtime logic from disk format.

#### 7.2. Local World State (Scene Snapshots)

- **Purpose**: Persisting the state of a dynamic world (e.g., 100 enemies, 50 chests) without creating thousands of global keys.
- **Mechanism**:
    - The `Scene` is responsible for serializing its own entities using a `WorldSerializer`.
    - This data is stored as a blob associated with the `(SceneID, SaveSlot)`.
    - On load, the Scene checks for a snapshot. If one exists, it hydrates the entities from the snapshot instead of the default level layout.

#### 7.3. The Lifecycle

1.  **Injection (Global Data)**
    - Scene declares `MANIFEST` for Session Data (e.g., `SessionKey.PLAYER_STATS`).
    - `SceneManager` injects these **References** into the Scene Context. Shared state means multiple stacked scenes see the same data object.

2.  **Hydration (Local Data)**
    - Scene `setup()` calls `WorldSerializer.load_or_default(scene_id)`.
    - This populates the ECS with entities.

3.  **Gameplay (No Manual Dirty Flags)**
    - Systems modify components normally.
    - We **removed manual dirty flags**. Instead, we rely on efficient full-state serialization (Snapshotting) at key moments (Checkpoints, Save Points, Scene Transitions).
    - *Optimization*: If performance becomes an issue, the `WorldSerializer` can implement internal diffing (comparing current hash vs last saved hash) transparently to the developer.

4.  **Commit (Persist)**
    - `SessionManager` serializes the Global State.
    - `WorldSerializer` serializes the Entity World.
    - Both are written to the persistence store transactionally.

#### 7.4. Benefits

- **Scalability**: Handles both the "Link" (Global) and "Pot" (Local/Dynamic) problems effectively.
- **Safety**: Removes the human error of "forgetting to mark dirty."
- **Robustness**: Migration Registry prevents save corruption when code changes.

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
            +-- [ECS World] (Entities: Loaded from Snapshot or Default)
            |    |
            |    +-- [Components] (Some are references to Session Data)
            |
            +-- [Systems]
```
