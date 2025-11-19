# Yukkuri Raising Game MVP

This project is a modern, data-driven reimagining of a "Yukkuri Raising Game," built with a clean architecture that separates the core game logic from the presentation layer. This MVP serves as a proof-of-concept, demonstrating the core gameplay loop with a simple Pygame-based UI.

## 1. Setup & Run

To get the game running, follow these steps:

**Prerequisites:**
*   Python 3.11+

**Installation:**
1.  Clone the repository to your local machine.
2.  Navigate to the project's root directory.
3.  Install the required dependencies, including Pygame:
    ```bash
    pip install -r requirements.txt
    ```

**Running the Game:**
Once the dependencies are installed, you can launch the game with the following command:
```bash
python -m game.adapters.pygame
```

## 2. Adding Content

The game is designed to be highly data-driven. You can add new content by creating new JSON files in the `/data` directory.

### Adding a New Yukkuri
1.  Create a new file in `/data/yukkuris/`.
2.  The filename should be the yukkuri's unique ID (e.g., `reimu.json`).
3.  The file must contain the following fields:
    ```json
    {
      "id": "reimu",
      "display_name_key": "yukkuri.reimu",
      "base_needs": {"hunger": 0.3, "energy": 0.7, "fun": 0.6},
      "personality": {"sociability": 0.8, "curiosity": 0.6},
      "ai_profile": "default_small"
    }
    ```

### Adding a New Item
1.  Create a new file in `/data/items/`.
2.  The filename should be the item's unique ID (e.g., `food_dispenser.json`).
3.  The file must contain the following fields:
    ```json
    {
      "id": "food_dispenser",
      "display_name_key": "item.food_dispenser",
      "size": {"w": 1, "h": 1},
      "tags": ["food_source"],
      "effects": {"hunger": {"rate": -0.1}}
    }
    ```
    *   `size`: The item's footprint on the placement grid.
    *   `tags`: Used by the AI to identify interaction points.
    *   `effects`: How the item modifies a yukkuri's needs when used.

### Adding a New AI Behavior
1.  Create a new file in `/data/behaviors/`.
2.  The filename is the ID of the AI profile (e.g., `cautious.json`).
3.  The file defines a list of `actions` and the `considerations` that score them:
    ```json
    {
      "actions": [
        {
          "id": "rest",
          "cooldown": 1.0,
          "considerations": [
            {"type": "need_inverse", "need": "energy", "curve": "quadratic", "weight": 1.0}
          ]
        },
        {
          "id": "eat_snack",
          "cooldown": 1.0,
          "considerations": [
            {"type": "need_level", "need": "hunger", "curve": "linear", "weight": 1.0}
          ]
        }
      ]
    }
    ```
    *   `type`: `need_level` (scores high when the need is high, e.g., hunger) or `need_inverse` (scores high when the need is low, e.g., energy).

## 3. Localization

All user-facing strings are managed through a simple key-value system.

*   To add a new language, create a new JSON file in `/data/localization/` (e.g., `jp.json`).
*   The file should contain a dictionary of keys to localized strings:
    ```json
    {
      "yukkuri.akari": "アカリ",
      "item.bed_simple": "シンプルなベッド"
    }
    ```
*   The game currently defaults to English (`en.json`).

## 4. Save/Load

*   The game's state can be saved and loaded from a JSON file.
*   The save file is a snapshot of the current game state, including the state of all yukkuris and placed items.
*   *Note: UI integration for save/load is not yet implemented in the MVP, but the core logic is in place.*

## 5. Web Port Notes

The project's architecture was intentionally designed to support a future web port with minimal changes to the core logic.

*   **Engine-Agnostic Core**: The entire `game/core/` directory is "engine-agnostic." It contains no Pygame-specific code and can be used with any presentation layer.
*   **Adapters**: To port the game to the web, you would create a new adapter (e.g., `game/adapters/web/`). This new adapter would be responsible for:
    *   Rendering the game state to an HTML5 canvas.
    *   Handling browser input events.
    *   Managing the game loop with `requestAnimationFrame`.
*   The core simulation, AI, data loading, and state management would remain unchanged.
