# Architecture Overview

This document provides a high-level overview of the Yukkuri Raising Game's software architecture.

## Guiding Principles

- **Data-Driven:** All game content, including agents, items, and actions, is defined in external JSON files. This allows for easy modification and expansion without code changes.
- **Layered Architecture:** The codebase is divided into distinct layers, each with a specific responsibility. This promotes separation of concerns and maintainability.
- **Extensibility:** The design is intended to be extensible, allowing for the future addition of new features, content, and even a web-based version.

## Core Layers

1.  **`engine/`**: This layer contains the fundamental, game-agnostic systems that form the core of the application.
    *   `serialization.py`: Manages saving and loading the game state to and from JSON files.
    *   *Future modules*: `event_bus.py`, `time_step.py` (currently integrated into `app.py`).

2.  **`simulation/`**: This layer is responsible for the core gameplay logic and the simulation of the Yukkuri world.
    *   `agent.py`: Defines the `Agent` class, which represents a single Yukkuri, including its state, needs, and actions.
    *   `needs.py`: Implements the `Need` class, which models an agent's needs (e.g., Hunger, Energy) and their decay over time.
    *   `actions.py`: Defines the `Action` class, which represents a behavior an agent can perform.
    *   `utility_ai.py`: Contains the `UtilityAI` class, which scores available actions based on an agent's needs and selects the best one.
    *   `world.py`: Manages the game world, including the grid, placed items, and placement rules.
    *   `pathfinding.py`: Implements the A* algorithm for agent navigation.
    *   `dialogue.py`: Manages the loading and serving of dialogue lines.

3.  **`game/`**: This layer handles the presentation, user interaction, and overall application flow.
    *   `app.py`: The main application class, which manages the game loop, window, and game modes.
    *   `game_modes.py`: Defines the different game modes, such as `LiveMode` and `PlacementMode`, which control the game's behavior in different states.
    *   `ui.py`: Manages the user interface, including the placement inventory and speech bubbles.
    *   `data_loader.py`: Handles the loading and parsing of the JSON data files.

4.  **`content/`**: This directory contains all the game's data and assets.
    *   `data/`: Contains the JSON files that define the game's content.
    *   `placeholders/`: Contains placeholder assets, such as images.

## Systems Overview

-   **Utility AI:** Agents use a utility-based AI to make decisions. Each tick, the AI evaluates all available actions, scores them based on the agent's current needs, and selects the action with the highest score.
-   **Placement System ("Yukkurrium"):** The player can enter a placement mode to place items in the world. The system uses a grid-based approach with collision detection to ensure valid placements.
-   **Save/Load System:** The game state can be serialized to a versioned JSON file, allowing the player to save and load their progress.
-   **Game Loop:** The main game loop uses a fixed timestep to ensure deterministic simulation, independent of the rendering frame rate.
