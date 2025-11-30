# Implementation Tasks (Revised)

This document outlines the actionable steps to implement the proposed architecture, revised to focus on simplicity, testing, and concrete deliverables.

## Phase 1: Core Engine & Testing Foundation

### 1.1. Application Skeleton & Test Harness
- [ ] Create `engine/application.py` (Main Loop, Window).
- [ ] Create `engine/scene.py` (Abstract Base Class).
- [ ] Create `engine/scene_manager.py` (Stack Management).
- [ ] **Verification**: Create a `TestScene` and write a unit test verifying the Application lifecycle (start, loop, stop) and Scene transitions.

### 1.2. Phase-Based Event System
- [ ] Create `engine/event_manager.py` (Phase dispatch: `PreUpdate`, `Update`, `PostUpdate`, `Render`).
- [ ] Implement `engine/events.py` with typed event classes (e.g., `EntityCreated`, `CollisionEvent`).
- [ ] **Verification**: Write tests ensuring events fired in `PreUpdate` are processed before `Update`.

### 1.3. Service Container
- [ ] Refactor `ServiceLocator` into a simple `ServiceContainer`.
- [ ] Register core services (Audio, Settings) at startup.
- [ ] **Verification**: Ensure services can be mocked in tests.

## Phase 2: Gameplay Logic Migration (Vertical Slice)

### 2.1. Scene Migration
- [ ] Move `MainMenu` logic to `scenes/main_menu.py`.
- [ ] Move `GameManager` loop logic to `scenes/gameplay.py`.
- [ ] **Verification**: specific test to ensure the game boots to Main Menu and transitions to Gameplay.

### 2.2. Input Refactoring
- [ ] Create `engine/input_manager.py` (Wrapper around hardware input).
- [ ] Implement simple `InputContext` (Enum: `GAMEPLAY`, `MENU`) to filter inputs.
- [ ] **Refactor**: Update `PlayerControlSystem` to query `InputManager` instead of raw hardware.

### 2.3. Entity Prefabs (Python)
- [ ] Create `game/prefabs/player.py`, `game/prefabs/enemy.py`.
- [ ] Refactor `EntityFactory` to simply call these functions.
- [ ] **Verification**: Unit test that instantiates a prefab and asserts it has correct components.

## Phase 3: Simple Persistence (MVP)

### 3.1. Basic Serialization
- [ ] Implement `engine/serializer.py`:
    - [ ] `serialize_entity(entity_id) -> dict`: Serializes all components.
    - [ ] `deserialize_entity(data) -> entity_id`: Recreates entity and components.
- [ ] **Verification**: Round-trip test (Serialize -> Deserialize -> Assert Equal).

### 3.2. World Saving (Synchronous)
- [ ] Implement `Scene.save(filepath)`:
    - [ ] Iterate all entities with `Persistable` component.
    - [ ] Serialize to JSON.
    - [ ] Write to disk synchronously.
- [ ] Implement `Scene.load(filepath)`:
    - [ ] Clear current world.
    - [ ] Load JSON, create entities.
- [ ] **Verification**: Integration test saving a scene with 10 entities and reloading it.

### 3.3. ID Management
- [ ] Implement `StableIDComponent` for entities that need to preserve identity (Player, Quest Items).
- [ ] Update `serializer` to respect `StableID` during load (restoring the ID instead of generating a new one).

## Phase 4: Cleanup & Documentation

### 4.1. System Cleanup
- [ ] Audit `CombatSystem` and `MovementSystem` to ensure they depend on Components, not global state.
- [ ] Remove legacy `GameManager` code.

### 4.2. Final Verification
- [ ] Run full test suite.
- [ ] Manual playtest of full loop (Menu -> Game -> Save -> Quit -> Load -> Game).
- [ ] Update `ARCHITECTURE.md` to reflect the *actual* implemented design.
