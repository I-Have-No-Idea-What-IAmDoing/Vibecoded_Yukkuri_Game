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
- [ ] Refactor systems to use direct observers (or signals/delegates) for high-frequency events where appropriate.

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

### 3.1. Data Persistence Infrastructure (Global State)
- [ ] Create `engine/persistence/keys.py` module for `Final` constant key definitions.
- [ ] Implement `engine/persistence/migration_registry.py` to handle versioned schema transformations.
- [ ] Create `engine/scene_context.py` to hold hydrated data for scene injection.
- [ ] Implement `SceneManager.hydrate_scene()`:
    - [ ] Resolve dependencies from `Scene.INJECTIONS`.
    - [ ] Load raw data and apply migrations via Registry.
    - [ ] Deserialize into target Component classes.
- [ ] Implement `SceneManager.snapshot_scene()`:
    - [ ] Collect data from `Scene.EXPORTS` (Main Thread).
    - [ ] Implement async background saver (serialization + disk I/O).
    - [ ] Ensure atomic file writes (temp file + rename).

### 3.2. Data Persistence Infrastructure (Dynamic World)
- [ ] Implement `engine/persistence/world_serializer.py`:
    - [ ] Create mechanism to iterate and serialize all entities with `Persistable` component.
    - [ ] Implement `UUIDComponent` for stable entity identification.
- [ ] Implement Entity Reference Resolution:
    - [ ] Implement two-pass loading (Create Entities -> Resolve References).
    - [ ] Update components referencing other entities to support ID remapping.

### 3.3. Pragmatic ECS Review
- [ ] Audit Components to add helper methods where they encapsulate data transformation (e.g., `is_dead()`).
- [ ] Ensure Systems focus on cross-component logic.
- [ ] Verify that "Game State" is correctly stored in Components or the Scene/Session, not cached in Systems.

### 3.4. Documentation & Tests
- [ ] Update `ARCHITECTURE.md` with the new design.
- [ ] Write unit tests for `EventManager`, `SceneManager`, `ActionMapper`, and Prefabs.
- [ ] Write unit tests for `MigrationRegistry` (chain validation, breaking/additive changes).
- [ ] Write integration tests for Save/Load cycle:
    - [ ] Ensure atomicity and version handling.
    - [ ] Verify entity reference integrity (ID remapping) after load.
    - [ ] Verify dynamic entities are correctly restored.
- [ ] Verify that the refactor hasn't introduced regressions in gameplay.
