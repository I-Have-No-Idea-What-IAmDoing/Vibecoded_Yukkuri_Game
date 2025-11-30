# Implementation Tasks (Revised v2)

This document outlines the actionable steps to implement the proposed architecture. The sequencing has been adjusted to prioritize a working vertical slice ("Walking Skeleton") before infrastructure refactoring, reducing the risk of integration hell.

## Phase 1: The Walking Skeleton (Migration First)

*Goal: Move the existing game into the new architectural structure without changing behavior. Prove the structure works with real code immediately.*

### 1.1. Application Shell
- [ ] Create `engine/application.py` (Main Loop, Window Wrapper).
- [ ] Create `engine/scene.py` (Abstract Base Class).
- [ ] Create `engine/scene_manager.py` (Stack Management).
- [ ] **Verification**: Run a "Hello World" scene that opens the window and closes on exit.

### 1.2. Scene Migration (The Hard Part)
- [ ] Create `scenes/main_menu.py` and port logic from `MainMenu`.
- [ ] Create `scenes/gameplay.py`.
- [ ] **Refactor**: Move `GameManager.update()` logic into `GameplayScene.update()`.
- [ ] **Refactor**: Move `GameManager.render()` logic into `GameplayScene.render()`.
- [ ] **Refactor**: Route existing raw input checks through the new `Application` loop to the active Scene.
- [ ] **Verification**: The game boots, plays, and closes exactly as it did before. The `GameManager` class is deleted or empty.

## Phase 2: System Refactoring (Clean Up)

*Goal: Now that the game is running in the new structure, replace legacy subsystems with the proposed robust designs.*

### 2.1. Phase-Based Event System
- [ ] Create `engine/event_manager.py` (Phase dispatch: `PreUpdate`, `Update`, `PostUpdate`, `Render`).
- [ ] Implement `engine/events.py` with typed event classes.
- [ ] **Refactor**: Replace direct system calls in `GameplayScene.update()` with event dispatching where appropriate.
- [ ] **Verification**: Ensure event processing order is correct (Pre -> Update -> Post).

### 2.2. Input System Refactor
- [ ] Create `engine/input_manager.py` (Wrapper around hardware input).
- [ ] Implement `InputContext` (Enum: `GAMEPLAY`, `MENU`) to filter inputs.
- [ ] **Refactor**: Update `PlayerControlSystem` and `MainMenu` to query `InputManager` instead of raw hardware.
- [ ] **Verification**: Verify that menu inputs are ignored during gameplay and vice versa.

### 2.3. Entity Prefabs
- [ ] Create `game/prefabs/player.py`, `game/prefabs/enemy.py`.
- [ ] **Refactor**: Replace usage of `EntityFactory` with direct calls to these prefab functions.
- [ ] **Verification**: Unit test that instantiates a prefab and asserts it has correct components.

## Phase 3: Simple Persistence (Corrected Order)

*Goal: Implement saving and loading, ensuring IDs are handled before serialization logic is written.*

### 3.1. Identity Management
- [ ] Implement `StableIDComponent` for entities that need to preserve identity (Player, Quest Items).
- [ ] ensure `Entity` creation allows assigning a specific ID (for loading).

### 3.2. Serialization Logic
- [ ] Implement `engine/serializer.py`:
    - [ ] `serialize_entity(entity_id) -> dict`: Serializes all components, preserving `StableID`.
    - [ ] `deserialize_entity(data) -> entity_id`: Recreates entity with the *same* `StableID`.
- [ ] **Verification**: Round-trip test (Serialize -> Deserialize -> Assert Equal IDs and Data).

### 3.3. World Saving (Synchronous)
- [ ] Implement `Scene.save(filepath)`:
    - [ ] Iterate all entities with `Persistable` component.
    - [ ] Serialize to JSON.
    - [ ] Write to disk synchronously.
- [ ] Implement `Scene.load(filepath)`:
    - [ ] Clear current world.
    - [ ] Load JSON, create entities.
- [ ] **Verification**: Integration test saving a scene with 10 entities, modifying the file manually (optional), and reloading it.

## Phase 4: Finalization

### 4.1. Cleanup & Docs
- [ ] Remove `ServiceLocator` *only if* it proves to be a hindrance; otherwise document its usage.
- [ ] Audit `CombatSystem` and `MovementSystem` to ensure they depend on Components, not global state.
- [ ] Update `ARCHITECTURE.md`.

### 4.2. Final Verification
- [ ] Run full test suite.
- [ ] Manual playtest of full loop (Menu -> Game -> Save -> Quit -> Load -> Game).
