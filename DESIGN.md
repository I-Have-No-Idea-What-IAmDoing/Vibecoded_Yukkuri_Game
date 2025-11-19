# Yukkuri Raising Game - Technical Design Summary

This document outlines the technical design for the Yukkuri Raising Game MVP.

## 1. Architecture Overview

The architecture is designed to be modular and data-driven, with a strict separation between the core domain logic and the presentation layer. This is often referred to as a "Clean Architecture" or "Hexagonal Architecture" approach.

-   **`game/core/`**: This is the heart of the application. It contains all the game's rules, logic, and state, but has no knowledge of how it will be presented. It is completely engine-agnostic and could be paired with any UI framework (Pygame, web, etc.).
-   **`game/adapters/pygame/`**: This is the implementation of the presentation layer using Pygame. It is responsible for rendering the game state provided by `core`, handling user input, and managing the main game loop. It is a "plugin" to the core.
-   **`data/`**: This directory holds all the game's content in JSON format. The game is data-driven, meaning that new yukkuris, items, and behaviors can be added by simply creating new JSON files, without changing the core code.

## 2. Module Responsibilities

### `game/core/`

-   **`ai/`**: Implements the Utility AI system. It defines actions, considerations (the scoring logic), and manages the decision-making process for each yukkuri.
-   **`ecs/`**: A lightweight entity management system. Instead of a full-blown ECS, this will be a simple system to manage game objects (yukkuris, items) and their associated data components.
-   **`sim/`**: Contains the core simulation logic. This includes the game clock, the system for updating yukkuri needs over time, and the rules for how yukkuris interact with each other and the environment.
-   **`data/`**: Handles loading, parsing, and validating the JSON data from the `/data` directory. It uses schema definitions to ensure data integrity and provides clear error messages for malformed files.
-   **`events/`**: A simple event bus for decoupled communication between different parts of the core logic. For example, when an action is performed, it can raise an event that other systems can listen to.
-   **`state/`**: Manages the overall game state, including the list of all entities, the player's inventory, and the game time. It will also be responsible for serialization and deserialization for the save/load functionality.
-   **`ui_model/`**: Defines the data structures that the UI will need, but without any Pygame-specific code. For example, it will define what information is needed to display a yukkuri's status panel, but not how to draw it.
-   **`localization/`**: A simple service for looking up localized strings by a given key.

### `game/adapters/pygame/`

-   **Rendering**: Translates the game state from `core` into visible objects on the screen.
-   **Input Handling**: Captures mouse and keyboard input and translates them into commands for the `core` (e.g., "place item at this position").
-   **Game Loop**: Manages the main game loop, including timing, pause/play, and speed controls.
-   **Scene Management**: Manages the different scenes of the game (e.g., main menu, game view).

## 3. Utility AI Design

The AI is based on a Utility AI architecture, which is excellent for modeling complex decision-making in a data-driven way.

-   **Actions**: An action is a behavior a yukkuri can perform (e.g., `Eat`, `Rest`, `Wander`). Each action is defined in the behavior JSON files.
-   **Considerations**: Each action has a list of considerations that are used to calculate a score for that action at a given moment. The score is a value between 0 and 1.
    -   **Scoring**: The final score for an action is the weighted average of all its consideration scores. The AI will choose the action with the highest score.
    -   **Curves**: Considerations use curves (e.g., linear, quadratic, inverse) to map a raw input value (like hunger level) to the 0-1 score.
-   **Blackboard**: Each yukkuri will have its own "blackboard" (a simple dictionary or data class) to store its current state, such as its needs, its current target, etc. There will also be a global blackboard for world state.
-   **Tick Cadence**: The AI will re-evaluate actions for each yukkuri on a regular cadence (e.g., once per second), with cooldowns on actions to prevent rapid switching.

## 4. Data Schemas & Validation

All game content will be defined in JSON. The data loaders in `game/core/data` will validate these files on startup.

-   **`yukkuris/*.json`**: Defines a type of yukkuri, its base needs, personality traits, and which AI profile it uses.
-   **`items/*.json`**: Defines an item, its size, tags (for interactions), and any effects it has on yukkuri needs.
-   **`behaviors/*.json`**: Defines an AI profile, which is a list of actions and their associated considerations.
-   **Validation**: We will use Python's `TypedDict` to define the expected structure of the JSON data. The data loader will attempt to parse the JSON into these typed dictionaries. If it fails, it will report a clear error message indicating which file is malformed and why.

## 5. Interaction Model

-   Yukkuris interact with items and other yukkuris based on the actions they choose.
-   The `tags` on an item are crucial. For example, an `Eat` action might look for a nearby item with the `food` tag.
-   When a yukkuri interacts with an item, the item's `effects` are applied. For example, interacting with a `bed_simple` item will increase the yukkuri's `energy` need.

## 6. Tank Customization

-   A simple grid-based system will be used for item placement.
-   Items have a `size` (width and height in grid cells).
-   The system will prevent items from being placed in occupied cells.
-   The player will have an inventory of items that they can place, move, and remove from the tank.

## 7. UI Design

The UI will be minimal for the MVP.

-   **Yukkuri Selection**: Clicking on a yukkuri will display its current needs and a summary of its state.
-   **Inventory Panel**: A simple panel to display the player's items and allow them to be selected for placement.
-   **Speech Bubbles**: Short text bubbles will appear above yukkuris to indicate their current action (e.g., "Eating", "Sleeping").
-   **Controls**: Buttons for pause/play and game speed.

## 8. Persistence

-   The game state will be saved to a simple JSON file.
-   This will be a "snapshot" of the entire game state, including the position and state of all yukkuris and items.

## 9. Localization

-   All user-facing strings will be looked up via a localization service.
-   The strings will be stored in `/data/localization/en.json` (and other languages in the future).
-   The lookup will be key-based (e.g., `localization.get("yukkuri.akari")`).

## 10. Web Port Path

The clean separation between `core` and `adapters` is the key to a future web port.

-   **What remains**: The entire `game/core` module can be used as-is. It contains no platform-specific code.
-   **What gets re-implemented**: A new adapter, `game/adapters/web/`, would be created. This adapter would:
    -   Render the game state to an HTML5 canvas instead of a Pygame window.
    -   Handle browser-based input events (mouse clicks, touch events).
    -   Use `requestAnimationFrame` for the game loop.
    -   Communicate with the core logic via the same interface that the Pygame adapter uses.
