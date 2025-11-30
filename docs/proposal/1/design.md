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

### 7. Description of data persistence between scenes

To ensure critical game data persists across scene boundaries (e.g. from Main Menu to Gameplay, or between Levels):

- **Session Context**: A dedicated `GameSession` object that lives within the `Application` scope, outside of any specific `Scene`.
- **State Separation**: Volatile level state remains in the `Scene` (ECS World), while persistent state (Inventory, Player Stats, Global Flags) is stored in the `GameSession`.
- **Serialization**: The `GameSession` is the primary target for Save/Load operations.
- **Injection**: The `GameSession` is passed to Scenes upon initialization or accessible via the `ServiceContainer`.

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
