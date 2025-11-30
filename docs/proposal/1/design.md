# Architecture Redesign Proposal (Revised)

## Overview

This proposal outlines a pragmatic refactoring of the Yukkuri Game Engine. The goal is to address specific scalability issues—specifically input handling, entity definition, and game state management—without over-engineering or introducing unnecessary abstraction layers.

## Core Components

### 1. Simplified Scene State Machine

Instead of a complex "Scene Stack", we will implement a deterministic **Scene State Machine**.

- **Application**: Initialization and main loop. Holds the *Current Scene*.
- **Scene Interface**: Defines `update()`, `render()`, `enter()`, and `exit()`.
- **Shared Context**: A data structure passed between scenes during transitions to persist state (e.g., Player Data, Global Inventory). This avoids the need for a complex stack while ensuring data continuity.

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

### 4. Validated Data-Driven Prefabs

Entities will be defined in data, but with strict validation to prevent runtime errors.

- **Schema Validation**: Use a library (e.g., Pydantic or specialized Schema validators) to validate YAML/TOML files at load time. Use "Fail Fast" principles.
- **PrefabManager**: Caches validated templates.
- **Instantiation**: `create_entity("name")` will raise a clear error if the name implies an invalid or missing template.

### 5. Pragmatic ECS

We will stick to ECS principles but relax dogmatic restrictions:

- **Components**: Primarily data, but **Helper Methods are allowed** (e.g., `health_component.is_dead()`, `velocity.add_impulse()`) to encapsulate local data transformations.
- **Systems**: Handle cross-component logic and interactions.
- **State**: Systems may cache query results or time-deltas for performance, but "Game State" remains in components or the Scene Context.

### 6. Service Access

A lightweight **ServiceContainer** will provide access to cross-cutting concerns (Audio, Logging, Assets).

- **Explicit Registration**: Services are registered at startup.
- **Facade**: The container acts as a facade, but systems should ideally take dependencies via `__init__` where feasible to improve testability.

## Architecture Diagram (Revised)

```
[Application]
  |
  +-- [ServiceContainer] (Audio, Assets, config)
  |
  +-- [SceneStateMachine]
       |
       +-- [Current Scene] <--> [Shared Context] (Inventory, PlayerStats)
            |
            +-- [ECS World]
                 |
                 +-- [Entities] (Validated via Schemas)
                 |
                 +-- [Systems] (Context-Aware Input, Logic)
```
