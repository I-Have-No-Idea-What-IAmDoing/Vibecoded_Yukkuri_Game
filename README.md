# Yukkuri Raising Game

A modern simulation game where you raise "Yukkuri" creatures in a virtual environment. Manage their needs, build their environment, and watch them interact.

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
- [Running the Game](#running-the-game)
- [Controls](#controls)
- [Gameplay Guide](#gameplay-guide)
- [Customization](#customization)
- [Project Structure](#project-structure)
- [Development](#development)
- [Documentation](#documentation)

## Overview

The **Yukkuri Raising Game** is a simulation game developed in Python using `pygame-ce` and `esper` (ECS). It simulates the lifecycle, behavior, and social interactions of Yukkuri creatures. The game features a robust Utility AI system, physics simulation, and data-driven content.

## Setup

### Prerequisites
- Python 3.11 or higher.

### Installation
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/yukkuri-raising-game.git
    cd yukkuri-raising-game
    ```

2.  **Create a virtual environment (optional but recommended)**:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On Unix/MacOS:
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    Install the package in editable mode with development dependencies:
    ```bash
    pip install -e .
    ```

## Running the Game

### Graphical Mode
To launch the game with the graphical interface:
```bash
python -m src.yukkuri_game.main
```

### Headless Mode
To run the simulation without a window (useful for testing or server-side simulation):
```bash
python -m src.yukkuri_game.main --headless
```

## Controls

-   **Camera Navigation**:
    -   **Zoom**: Mouse Wheel Scroll, or `Ctrl + =` / `Ctrl + -`.
    -   **Pan**: Hold Middle Mouse Button (Scroll Wheel Click) and Drag, or `WASD` / Arrow Keys.

-   **Interaction**:
    -   **Select Entity**: Left Click on a Yukkuri or Item.
    -   **Multi-Select**: Hold `Shift` + Left Click to add to selection, or Drag with Left Click on empty space to box select.
    -   **Deselect**: Left Click on empty ground (without dragging).
    -   **Place Item/Yukkuri**: Select an item from the bottom bar, then Left Click in the world.
    -   **Cancel Placement**: Right Click while in placement mode.
    -   **Context Menu**: Right Click on an entity (Not fully implemented in MVP).

-   **HUD Shortcuts**:
    -   **F3**: Toggle Debug Info Overlay.
    -   **F5**: Quick Save.
    -   **F9**: Quick Load.
    -   **F12**: Take Screenshot (saved to `screenshots/`).

## Gameplay Guide

### The Interface (HUD)
-   **Top Bar**:
    -   **Money**: Your current funds.
    -   **Time**: Elapsed game time.
    -   **Time Controls**: Pause/Resume and cycle Speed (1x, 2x, 5x, 0.5x).
    -   **Save/Load**: Persist your game state.
    -   **Settings**: Adjust volume and window settings.
-   **Bottom Bar**:
    -   **Log**: Displays game events and notifications.
    -   **Buy Buttons**: Purchase new Yukkuris (e.g., Reimu) or Items (e.g., Cookie, Bed).
    -   **Tools**: Clean Tool for removing waste.

### Managing Yukkuris
Click on a Yukkuri to view its details in the **Entity Info** window on the right.
-   **Stats**: Monitor Hunger, Happiness, Health, Social, Stress, and Badges.
-   **Sell**: Sell the Yukkuri for money based on its quality score.
-   **Train**: Train the Yukkuri to increase its Badge count and Happiness.
-   **Punish**: Punish the Yukkuri to increase Discipline (but lowers Health/Happiness).

### Economy
-   **Starting Funds**: You begin with $1000.
-   **Expenses**: Buy Food, Toys, and Beds to keep Yukkuris happy and healthy.
-   **Profit**: Sell well-raised (high stats, badges, age) Yukkuris to make a profit.

## Customization

The game is heavily data-driven using TOML files located in the `data/` directory.

### Adding a New Yukkuri Type
Edit `data/yukkuris/types.toml`:
```toml
[yukkuris.new_type]
name = "New Type"
image = "new_type.png" # Place image in assets/images/
width = 64
height = 64
max_health = 120
base_happiness = 50
cost = 150
```

### Adding a New Item
Edit `data/items/items.toml`:
```toml
[items.super_cookie]
name = "Super Cookie"
image = "super_cookie.png"
width = 32
height = 32
cost = 100
nutrition = 50
fun = 20
comfort = 5
is_portable = true
```

### Configuring AI
Edit `data/ai/actions.toml` to define new Utility Actions.
Edit `data/ai/interactions.toml` to define social interaction outcomes.
Edit `data/traits/traits.toml` to define personality traits and their modifiers.

## Project Structure

This project follows a modular structure separating core engine features from game-specific logic.

-   `src/yukkuri_game/engine/`: **Core Engine Framework**
    -   `ecs.py`: A wrapper around `esper` providing an Entity Component System.
    -   `event_bus.py`: A publish-subscribe event system for decoupled communication.
    -   `resource_manager.py`: Handles loading and caching of assets and data (TOML).
    -   `audio.py`: Manages sound playback via `pygame.mixer`.
    -   `service_locator.py`: Provides global access to essential services.
    -   `core.py`: Contains the main `GameLoop` class.

-   `src/yukkuri_game/game/`: **Game Logic Implementation**
    -   `ai/`: Artificial Intelligence modules (Utility AI, Behavior Trees, Navigation).
    -   `systems/`: **ECS Systems** handling logic for each frame (e.g., `PhysicsSystem`, `SocialSystem`).
    -   `ui/`: **User Interface** built with `pygame_gui`.
    -   `components.py`: **Generic Components** (e.g., `Transform`, `Sprite`).
    -   `yukkuri_components.py`: **Game-Specific Components** (e.g., `YukkuriStats`, `Personality`).
    -   `entity_factory.py`: Centralized factory for creating entities.
    -   `services.py`: Game Services (Economy, Time, Persistence, Input).
    -   `renderer.py`: World rendering and camera management.

-   `src/yukkuri_game/scenes/`: **Scene Management**
    -   `main_menu.py`: The main menu screen.
    -   `gameplay.py`: The main gameplay loop and initialization.

-   `src/yukkuri_game/testing/`: **Testing Infrastructure**
    -   `driver.py`: Automated game driver for headless testing.
    -   `environment.py`: Context manager for headless environment setup.

-   `data/`: **Data-Driven Configuration**
    -   Contains TOML files defining game content and rules.

-   `assets/`: **Static Assets**
    -   Contains images and sound files.

## Development

The codebase is fully documented using **Google Style Python Docstrings**. Every public function, method, and class includes a docstring detailing its purpose, arguments, and return values. This comprehensive documentation supports new developers in understanding and extending the engine.

### Documentation Standards
When contributing, ensure all new code includes comprehensive docstrings:

```python
def calculate_quality_score(self, yukkuri_stats: YukkuriStats) -> int:
    """
    Calculates the quality score (value) of a Yukkuri.

    Args:
        yukkuri_stats (YukkuriStats): The stats component of the Yukkuri.

    Returns:
        int: The calculated value in money.
    """
```

### Testing
Run tests using `pytest`. The tests use a headless driver to simulate game logic without a window.
```bash
pytest
```

## Documentation

For more detailed information, please refer to the documents in the `docs/` folder:

-   [Contributing Guidelines](docs/CONTRIBUTING.md)
-   [Architecture Overview](docs/ARCHITECTURE.md)
-   [Data Driven Design](docs/DATA_DRIVEN_DESIGN.md)
-   [AI System](docs/ai_system.md)
-   [Animation System](docs/animation.md)
-   [Headless Testing](docs/headless_testing.md)
-   [FAQ](docs/FAQ.md)
