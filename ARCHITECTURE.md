# Yukkuri Game Engine Architecture

## Overview

This document outlines the architecture of the Yukkuri Game Engine, focusing on modularity, scalability, and maintainability.

## Core Components

### 1. Application Lifecycle & Scene Management

- **Application (`engine/application.py`)**: The entry point. Handles the main loop, window management, and initializes the `SceneManager`.
- **SceneManager (`engine/scene_manager.py`)**: Manages a stack of `Scene` objects (push, pop, replace).
- **Scene (`engine/scene.py`)**: Abstract base class for game states (e.g., `MainMenuScene`, `GameplayScene`). Each Scene owns its own ECS `World`.

### 2. Entity Component System (ECS)

- **ECS Wrapper (`engine/ecs.py`)**: Wraps the `esper` library to provide a context-based `World` API.
- **Components**: Data containers (mostly `dataclasses`).
- **Systems**: Logic processors that operate on entities with specific components.

### 3. Event System (`engine/event_manager.py`)

- **Phase-Based Dispatch**: Events are processed at specific phases (`PreUpdate`, `Update`, `PostUpdate`).
- **Event Bus (`engine/event_bus.py`)**: Handles subscription and publishing of typed events.
- **Typed Events (`engine/events.py`)**: All events are dataclasses for type safety.

### 4. Input System (`engine/input_manager.py`)

- **Context-Aware**: `InputManager` manages `InputContext`s (e.g., `GAMEPLAY`, `MENU`).
- **Action Mapping**: Maps physical keys to logical actions.

### 5. Prefabs (`game/prefabs/`)

- Python functions (e.g., `create_yukkuri`) that construct and return fully configured entities.
- Replaces configuration files for entity definition logic.

### 6. Service Access (`engine/service_locator.py`)

- **ServiceLocator**: Provides access to cross-cutting concerns (Audio, Logging, Assets) via `world.services`.
- **Registration**: Services are registered at startup or scene initialization.

### 7. Persistence (`engine/serializer.py`)

- **Snapshot-Based**: The world state is serialized to MessagePack (via `msgspec`) for performance and compactness.
- **Components**: `Persistable` marker component indicates entities to save. `StableIDComponent` ensures identity preservation across saves.
- **Serializer**: `WorldSerializer` handles serialization/deserialization, including reference resolution for Entity IDs.

## Directory Structure

- `engine/`: Core engine systems (Application, ECS, Input, Events, Audio, Serializer).
- `game/`: Game-specific logic (Components, Systems, Prefabs).
- `scenes/`: Scene implementations.
- `assets/`: Game assets.

## Usage

### Adding a New Entity
Define a prefab function in `game/prefabs/` that creates an entity and adds components.

### Adding a New System
Inherit from `System` in `engine/ecs.py` and implement `update(self, world, dt)`. Register it in the `Scene`.

### Saving/Loading
Call `scene.save(filepath)` or `scene.load(filepath)`. Ensure entities have `Persistable` and `StableIDComponent`.
