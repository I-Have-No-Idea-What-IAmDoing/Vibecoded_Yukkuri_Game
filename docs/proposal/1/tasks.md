# Implementation Tasks (Revised)

This document outlines the actionable steps to implement the pragmatic architecture.

## Phase 1: Core Lifecycle & Scenes

### 1.1. Application & State Machine
- [ ] Create `engine/application.py` to handle the main loop and `ServiceContainer` initialization.
- [ ] Create `engine/scene.py` interface (`enter`, `exit`, `update`, `render`).
- [ ] Implement `engine/scene_manager.py` as a simple State Machine (no stack, just current/next).
- [ ] Define `SharedContext` class for data persistence between scenes.

### 1.2. Phase-Based Events
- [ ] Implement `EventManager` with simple, typed event dispatch.
- [ ] Define frame phases (`PreUpdate`, `Update`, `PostUpdate`) in the Application loop.

## Phase 2: Input & Data

### 2.1. Context-Aware Input
- [ ] Create `engine/input/action_mapper.py` supporting multiple contexts (e.g., `Context("menu")`, `Context("gameplay")`).
- [ ] Implement `InputSystem` that queries the `ActionMapper` based on the active context stack.
- [ ] Migrate `InputSystem` to use context-aware checks.

### 2.2. Validated Prefabs
- [ ] Select a validation library (e.g., Pydantic or `schema`).
- [ ] Define schemas for existing Components.
- [ ] Create `engine/prefab_manager.py` that loads AND validates YAML/TOML files against schemas.
- [ ] Migrate Yukkuri entity creation to use validated prefabs.

## Phase 3: Cleanup

### 3.1. Pragmatic Refactoring
- [ ] Move utility logic into Component methods where it clarifies code (e.g., `Position.distance_to()`).
- [ ] Remove `GameManager` and distribute responsibilities to `SceneManager` and `Application`.

### 3.2. Verification
- [ ] Write tests for `SchemaValidation` (ensure bad data fails to load).
- [ ] Verify Input Context switching works (e.g., opening a menu stops player movement).
