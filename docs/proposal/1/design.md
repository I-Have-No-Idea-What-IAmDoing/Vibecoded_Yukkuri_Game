# Architecture Redesign Proposal

## Overview

This proposal outlines a refined architecture for the Yukkuri Game Engine. The goal is to enhance modularity, scalability, and maintainability by adopting strict separation of concerns and data-driven design principles.

## Core Components

### 1. Application Lifecycle & Scene Management

The current `GameManager` handles too many responsibilities. We propose splitting it into an `Application` class and a `SceneManager`.

- **Application**: Responsible for initializing the engine, the main loop, and window management. It owns the `SceneManager`.
- **SceneManager**: Manages a stack of `Scene` objects. It handles transitions (push, pop, replace).
- **Scene**: A container for a specific game state (e.g., `MainMenuScene`, `GameplayScene`). Each Scene owns its own ECS World and specific Systems.

### 2. Enhanced Event System

The current `EventBus` is functional but basic. We propose a more robust `EventManager` that supports:

- **Channels/Topics**: Logical grouping of events.
- **Immediate vs. Queued Dispatch**: Support for immediate callbacks and frame-delayed processing to prevent call stack explosion and infinite loops.
- **Prioritized Listeners**: Ability to control the order in which listeners receive events.

### 3. Input Abstraction Layer

Move away from checking specific keys in systems. Introduce an **Action-based Input System**.

- **InputManager**: Captures raw hardware events (keyboard, mouse).
- **ActionMapper**: Maps raw inputs to logical Actions (e.g., `Key.SPACE` -> `Action.JUMP`). This allows for easy key remapping and multi-device support.
- Systems query `ActionMapper.is_action_pressed("JUMP")` instead of `Input.is_key_pressed(Key.SPACE)`.

### 4. Data-Driven Entity Factory (Prefabs)

Expand the `EntityFactory` to support **Prefabs** defined in external data files (YAML or TOML).

- **PrefabManager**: Loads and caches entity templates.
- **Template Definition**: YAML/TOML files defining components and initial values.
- **Instantiation**: Creating an entity by name (e.g., `create_entity("yukkuri_baby")`). This removes hardcoded entity assembly from Python code.

### 5. Strict ECS Separation

Reinforce ECS boundaries:

- **Components**: Pure data classes (dataclasses). No logic.
- **Systems**: Logic only. Stateless where possible.
- **World**: The container and query interface.

### 6. Service Architecture

Refine the `ServiceLocator` into a centralized `ServiceContainer` initialized at startup.

- Services (Audio, Economy, Persistence) should be registered explicitly.
- Dependency Injection: Systems can request services via the container, reducing global state usage.

## Architecture Diagram (Conceptual)

```
[Application]
  |
  +-- [ServiceContainer] (Audio, Input, Resources, Settings)
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
