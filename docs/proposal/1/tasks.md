# Implementation Tasks

This document outlines the actionable steps to implement the proposed architecture.

## Phase 1: Core Engine Refactoring

### 1.1. Application & Scene System
- [ ] Create `engine/application.py` class to handle main loop and window.
- [ ] Create `engine/scene.py` abstract base class.
- [ ] Create `engine/scene_manager.py` to handle scene stack.
- [ ] Refactor `main.py` to use `Application`.
- [ ] Move current game logic from `GameManager` to `GameplayScene`.

### 1.2. Phase-Based Event System
- [ ] Create `engine/event_manager.py` with support for phase-based dispatch.
- [ ] Define standard frame phases (`PreUpdate`, `Update`, `PostUpdate`, `Render`).
- [ ] Implement typed event classes.
- [ ] Refactor systems to use direct observers for high-frequency events where appropriate.

### 1.3. Service Access
- [ ] Refactor `ServiceLocator` into `ServiceContainer` acting as a facade.
- [ ] Ensure all services (Audio, Settings, etc.) are registered during Application startup.
- [ ] Update Systems to accept dependencies via `__init__` or use the Container.

## Phase 2: Input & Prefabs

### 2.1. Context-Aware Input
- [ ] Create `engine/input/input_manager.py` for raw input.
- [ ] Create `engine/input/action_mapper.py` for logical mapping.
- [ ] Implement `InputContext` system to manage active mappings (e.g., Menu vs Gameplay).
- [ ] Refactor `InputSystem` to support context switching and priority.

### 2.2. Pythonic Prefabs
- [ ] Create `game/prefabs/` directory (as a Python package).
- [ ] Refactor `EntityFactory` to delegate to prefab functions.
- [ ] Migrate existing entity creation logic to Python prefab modules/functions.
- [ ] Ensure prefabs return fully configured Entity instances.

## Phase 3: Persistence & Cleanup

### 3.1. Data Persistence
- [ ] Create `engine/session.py` (or `GameSession`) to hold persistent state.
- [ ] Integrate Session with `Application` and `ServiceContainer`.
- [ ] Update persisted Components to inherit from `msgspec.Struct`.
- [ ] Implement `PersistenceSystem` to handle dirty flags and incremental serialization using `msgspec.msgpack`.

### 3.2. Pragmatic ECS Review
- [ ] Audit Components to add helper methods where they encapsulate data transformation (e.g., `is_dead()`).
- [ ] Ensure Systems focus on cross-component logic.
- [ ] Verify that "Game State" is correctly stored in Components or the Scene/Session, not cached in Systems.

### 3.3. Documentation & Tests
- [ ] Update `ARCHITECTURE.md` with the new design.
- [ ] Write unit tests for `EventManager`, `SceneManager`, `ActionMapper`, and Prefabs.
- [ ] Verify that the refactor hasn't introduced regressions in gameplay.
