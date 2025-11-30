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

To avoid the pitfalls of shared mutable global state and ensure data integrity, we will adopt a **Hydration/Dehydration** model for persistence.

#### 7.1. Core Principles

- **No Global Session in ECS**: Systems inside a Scene **never** access a global `GameSession`, `SaveFile`, or `Database` object directly. They operate exclusively on local Components.
- **Explicit Data Transfer**: Data moving between the permanent storage (Session) and the active game (Scene) is always explicit, typed, and snapshotted.
- **Source of Truth**:
    - During a Scene's lifecycle, the **ECS World is the single source of truth**.
    - The persistent storage is updated only during transition boundaries or explicit checkpoints, preventing desync bugs.

#### 7.2. The Lifecycle

1.  **Hydration (Input)**
    - When the `SceneManager` pushes a new Scene, it extracts necessary data from the Master Save State.
    - It creates a **SceneContextDTO** (Data Transfer Object). This is a read-only, immutable structure (e.g., a frozen Python dataclass).
    - **Example**:
      ```python
      @dataclass(frozen=True)
      class GameplayContext:
          player_stats: PlayerStatsDTO
          inventory: List[ItemDTO]
          active_quests: List[QuestID]
      ```
    - The Scene's `Initializer` receives this DTO and populates the ECS World. It spawns the Player Entity and attaches `StatsComponent` and `InventoryComponent` filled with values from the DTO.

2.  **Gameplay (Simulation)**
    - Systems modify Components. For example, the `CombatSystem` reduces `StatsComponent.hp`.
    - The original DTO is ignored; it is merely the "seed" for the simulation.
    - The Master Save State is **not** modified during this phase.

3.  **Dehydration (Output)**
    - When a Scene is suspended, unloaded, or a checkpoint is reached, the Scene performs an export.
    - A specialized `PersistenceSystem` (or a `Scene.export_state()` method) queries the ECS World.
    - It constructs a **SceneResultDTO** containing the new state of persistent elements.
    - **Example**:
      ```python
      def export_state(self, world) -> GameplayResult:
          player = world.get_entity_by_tag("player")
          return GameplayResult(
              player_stats=player.get(StatsComponent).to_dto(),
              inventory=player.get(InventoryComponent).to_dto(),
              ...
          )
      ```

4.  **Merging**
    - The `SceneManager` receives the `SceneResultDTO`.
    - It passes this result to the `Application`'s Session Manager.
    - The Session Manager merges the changes back into the Master Save State, handling any necessary logic (e.g., unlocking achievements based on the result).

#### 7.3. Benefits

- **Testability**: Scenes can be tested in isolation by injecting mock DTOs. You don't need a complex database or save file reader to test the `GameplayScene`.
- **Determinism**: Since input state is explicit, reproducing bugs involves simply capturing the input DTO.
- **Modularity**: The data format of the Save File is decoupled from the runtime Components. A migration layer can exist between the Save File loading and the creation of the DTOs.

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
