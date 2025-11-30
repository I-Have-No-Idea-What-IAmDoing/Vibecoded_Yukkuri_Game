# Implementation Tasks

This document outlines the actionable steps to implement the proposed architecture.

## Phase 1: Core Engine Refactoring

### 1.1. Application & Scene System
- [ ] Create `engine/application.py` class to handle main loop and window.
- [ ] Create `engine/scene.py` abstract base class.
- [ ] Create `engine/scene_manager.py` to handle scene stack.
- [ ] Refactor `main.py` to use `Application`.
- [ ] Move current game logic from `GameManager` to `GameplayScene`.

### 1.2. Enhanced Event System
- [ ] Create `engine/event_manager.py` with support for immediate and queued events.
- [ ] Implement topic/channel based subscription.
- [ ] Replace usage of `EventBus` with new `EventManager` across the codebase.

### 1.3. Service Container
- [ ] Refactor `ServiceLocator` into `ServiceContainer`.
- [ ] Ensure all services (Audio, Settings, etc.) are registered during Application startup.

## Phase 2: Input & Data-Driven Systems

### 2.1. Input Abstraction
- [ ] Create `engine/input/input_manager.py` for raw input.
- [ ] Create `engine/input/action_mapper.py` for logical mapping.
- [ ] Define default keybindings in a configuration file (YAML/TOML).
- [ ] Refactor `InputSystem` and other systems to use `ActionMapper`.

### 2.2. Prefab System
- [ ] Design YAML/TOML schema for Entity Prefabs.
- [ ] Create `engine/prefab_manager.py` to load and validate prefabs.
- [ ] Refactor `EntityFactory` to use `PrefabManager` for entity creation.
- [ ] Migrate existing hardcoded entities (Yukkuri, Items) to YAML/TOML prefab files.

## Phase 3: Cleanup & Optimization

### 3.1. ECS Strictness
- [ ] Audit all Components to ensure they contain NO logic methods.
- [ ] Audit all Systems to ensure they store NO state (state should be in Components or Resources).

### 3.2. Documentation & Tests
- [ ] Update `ARCHITECTURE.md` with the new design.
- [ ] Write unit tests for `EventManager`, `SceneManager`, and `ActionMapper`.
- [ ] Verify that the refactor hasn't introduced regressions in gameplay.
