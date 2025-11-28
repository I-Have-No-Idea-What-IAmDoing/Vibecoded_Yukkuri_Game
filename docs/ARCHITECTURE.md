# Architecture

The Yukkuri Raising Game is built on a modular architecture designed to separate concerns and allow for data-driven content.

## Core Components

### 1. Entity Component System (ECS)

The game uses the **Entity Component System** pattern, implemented using the `esper` library and wrapped in `src/yukkuri_game/engine/ecs.py`.

*   **Entities**: Integers representing objects in the game world. They have no data or behavior themselves but are containers for components.
*   **Components**: Data classes that hold state (e.g., `Transform`, `Velocity`, `Sprite`, `YukkuriStats`). Components have no behavior.
*   **Systems**: Logic processors that operate on entities with specific components. Examples: `MovementSystem`, `RenderSystem`, `BehaviorSystem`.

This approach decouples data from logic, making it easier to add new features without modifying existing classes.

### 2. Event Bus

The **Event Bus** (`src/yukkuri_game/engine/event_bus.py`) provides a publish-subscribe mechanism for decoupled communication between systems.

*   **Publishers**: Any part of the code can publish an event (e.g., "yukkuri_died", "item_placed").
*   **Subscribers**: Systems or other components can subscribe to specific event types and react to them.

This avoids tight coupling where one system needs to directly call methods on another.

### 3. Service Locator

The **Service Locator** (`src/yukkuri_game/engine/service_locator.py`) provides global access to essential services that don't fit well into the ECS model or need to be shared widely.

*   **Services**: `ResourceManager`, `AudioManager`, `InputService`, `TimeService`, `EconomyService`.
*   **Access**: `ServiceLocator.get_service("name")`.

### 4. Game Loop

The `GameLoop` (`src/yukkuri_game/engine/core.py`) manages the main execution loop.

1.  **Process Input**: Collects events from Pygame (keyboard, mouse).
2.  **Update**: Advances the game state by calling `world.update(dt)`.
3.  **Render**: Draws the current state to the screen.

## Directory Structure

*   `src/yukkuri_game/engine/`: Generic game engine code (ECS wrapper, Event Bus, etc.).
*   `src/yukkuri_game/game/`: Game-specific logic (Systems, Components, UI).
*   `src/yukkuri_game/game/systems/`: ECS Systems.
*   `src/yukkuri_game/game/components.py`: General components.
*   `src/yukkuri_game/game/yukkuri_components.py`: Game-specific components.
*   `data/`: TOML configuration files.
*   `assets/`: Images and sounds.

## Data Flow

1.  **Initialization**:
    *   `GameConfig` loads settings from `data/`.
    *   `ResourceManager` loads assets.
    *   `YukkuriGame` initializes the World, adds Systems, and starts the loop.

2.  **Update Loop**:
    *   `TimeService` calculates delta time (`dt`).
    *   `InputSystem` processes user input and updates `InputComponent`s.
    *   `BehaviorSystem` updates AI decision trees.
    *   `PhysicsSystem` updates positions based on velocity and collisions.
    *   `RenderSystem` draws entities to the screen.

3.  **Inter-System Communication**:
    *   Systems communicate via components (e.g., AI sets `Target` component, Movement reads it).
    *   Systems communicate via events (e.g., `DeathSystem` publishes `EntityDiedEvent`, `SocialSystem` hears it and reduces happiness of friends).
