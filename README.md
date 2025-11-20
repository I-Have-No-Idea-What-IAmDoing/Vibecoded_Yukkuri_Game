# Yukkuri Raising Game - MVP

A simulation game where you raise "Yukkuri" creatures in a virtual environment. Manage their needs, build their environment, and watch them interact.

## Table of Contents
- [Setup](#setup)
- [Running the Game](#running-the-game)
- [Controls](#controls)
- [Gameplay Guide](#gameplay-guide)
- [Customization](#customization)
- [Project Structure](#project-structure)

## Setup

1.  **Prerequisites**: Ensure Python 3.11 or higher is installed.
2.  **Install Dependencies**:
    Navigate to the root directory of the project and install the package in editable mode:
    ```bash
    pip install -e .
    ```

## Running the Game

To launch the game with the graphical interface:
```bash
python -m src.yukkuri_game.main
```

To run in headless mode (no window, useful for testing or servers):
```bash
python -m src.yukkuri_game.main --headless
```

## Controls

-   **Camera Navigation**:
    -   **Zoom**: Mouse Wheel Scroll.
    -   **Pan**: Hold Middle Mouse Button (Scroll Wheel Click) and Drag.

-   **Interaction**:
    -   **Select Entity**: Left Click on a Yukkuri or Item.
    -   **Multi-Select**: Hold `Shift` + Left Click (not fully implemented in MVP).
    -   **Deselect**: Left Click on empty ground.
    -   **Place Item/Yukkuri**: Left Click while in placement mode.
    -   **Cancel Placement**: Right Click while in placement mode.

-   **Shortcuts**:
    -   **F3**: Toggle Debug Info Overlay.
    -   **F12**: Take Screenshot (saved to `screenshots/`).

## Gameplay Guide

### The Interface (HUD)
-   **Top Bar**:
    -   **Money**: Your current funds.
    -   **Time**: Elapsed game time.
    -   **Time Controls**: Pause/Resume and cycle Speed (1x, 2x, 5x, 0.5x).
    -   **Save/Load**: Persist your game state.
-   **Bottom Bar**:
    -   **Buy Buttons**: Purchase new Yukkuris (e.g., Reimu) or Items (e.g., Cookie).

### Managing Yukkuris
Click on a Yukkuri to view its details in the **Entity Info** window on the right.
-   **Stats**: Monitor Hunger, Happiness, Health, and Badges.
-   **Sell**: Sell the Yukkuri for money based on its quality (Health, Happiness, Badges, Age).
-   **Train**: Train the Yukkuri to increase its Badge count and Happiness.

### Economy
-   Start with $1000.
-   Buy Items to keep Yukkuris happy and fed.
-   Sell well-raised Yukkuris to make a profit.

## Customization

The game is data-driven using TOML files in the `data/` directory.

### Adding a New Yukkuri Type
Edit `data/yukkuris/types.toml`:
```toml
[yukkuris.new_type]
name = "New Type"
image = "image.png" # Place image in assets/images/
max_health = 100
width = 64
height = 64
```

### Adding a New Item
Edit `data/items/items.toml`:
```toml
[items.new_item]
name = "New Item"
image = "item.png"
cost = 50
nutrition = 10
fun = 5
```

### AI Behavior
Edit `data/ai/actions.toml` to define new Utility Actions, Considerations, and Effects.

Example Action:
```toml
[actions.Eat]
weight = 2.0
[actions.Eat.effects]
type = "interact_item"
target_stat = "nutrition"
consume = true
stat_changes = { hunger = -20.0, happiness = 5.0 }

[[actions.Eat.considerations]]
name = "Hunger"
input = "hunger"
curve = "linear"
params = { m = 1.0, b = 0.0 }
```

## Project Structure

-   `src/yukkuri_game/engine/`: Core engine components (Audio, ECS, GameLoop, ResourceManager).
-   `src/yukkuri_game/game/`: Game-specific logic.
    -   `ai/`: Utility AI and Pathfinding.
    -   `systems/`: ECS Systems (Simulation).
    -   `ui/`: HUD and UI management.
    -   `components.py`: ECS Components.
    -   `entity_factory.py`: Creator for game entities.
-   `data/`: Configuration files (TOML).
-   `assets/`: Game assets (Images, Sounds).
