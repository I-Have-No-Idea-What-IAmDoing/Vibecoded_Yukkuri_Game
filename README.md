# Yukkuri Raising Game

## Overview

This project is a modern reimagining of the classic fan game "Yukkuri Hakkei," built with Python and Pygame-ce. The game is a Minimum Viable Product (MVP) that demonstrates the core gameplay loop and foundational systems of a Yukkuri raising simulator.

## Features

*   **Raise, Care, and Grow**: Manage a "Yukkurrium" where Yukkuris autonomously manage their needs, grow through life stages, and interact with their environment.
*   **Utility-Based AI**: Yukkuris make decisions based on a utility AI system, with behaviors defined in external data files.
*   **Data-Driven Design**: All game data, from Yukkuri types to AI actions, is loaded from TOML files, allowing for easy modification and expansion.
*   **Game Economy**: Raise Yukkuris to increase their "Quality Score," then sell them to earn in-game currency.
*   **Persistence**: Save and load your game state at any time.

## Setup Instructions

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/Yukkuri-Raising-Game.git
    cd Yukkuri-Raising-Game
    ```

2.  **Install dependencies**:
    Make sure you have Python 3.10+ installed. Then, install the required libraries using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the game**:
    To run the game, execute the `main.py` script as a module from the project's root directory:
    ```bash
    python3 -m src.main
    ```

## How to Add New Content

The game is designed to be easily extensible by modifying the data files in the `data/` directory.

### Adding a New Yukkuri Type

1.  Open `data/yukkuri_types.toml`.
2.  Add a new entry with a unique name (e.g., `[chen]`).
3.  Define the following properties:
    *   `name`: The display name of the Yukkuri (e.g., "Chen").
    *   `base_health`: The starting health of the Yukkuri.
    *   `base_happiness`: The starting happiness of the Yukkuri.

**Example**:
```toml
[chen]
name = "Chen"
base_health = 90
base_happiness = 110
```

### Adding a New Item

1.  Open `data/item_types.toml`.
2.  Add a new entry with a unique name (e.g., `[catnip]`).
3.  Define the following properties:
    *   `name`: The display name of the item (e.g., "Catnip").
    *   `type`: The type of item (e.g., "toy", "food").
    *   `value`: The effect of the item (e.g., the amount of happiness or hunger it restores).

**Example**:
```toml
[catnip]
name = "Catnip"
type = "toy"
value = 25
```

### Adding a New AI Action

1.  Open `data/ai_config.toml`.
2.  Add a new action block with a unique name (e.g., `[explore]`).
3.  Define the considerations that influence the action's utility score. Each consideration should have a `curve` and `params`.

**Example**:
```toml
[explore]
# This action is driven by boredom (low happiness).
[explore.considerations.happiness]
curve = "linear"
params = { m = -0.008, b = 0.9 } # Higher utility when happiness is low
```
