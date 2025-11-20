# Yukkuri Raising Game MVP

This is a Minimum Viable Product for a data-driven Yukkuri raising game.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install pygame-ce PyYAML
    ```

2.  **Run the Game**:
    ```bash
    python main.py
    ```

## Controls

*   **Left Click**: Select a Yukkuri or Place an Item.
*   **Keys 1-3**: Select Item to Place.
    *   1: Bean Paste ($10)
    *   2: Sweet Bun ($25)
    *   3: Soft Bed ($100)
*   **S**: Sell the currently selected Yukkuri.
*   **Space**: Spawn a debug Reimu.
*   **F5**: Save Game.
*   **F9**: Load Game.
*   **ESC**: Quit.

## Extension Guide

The game is designed to be purely data-driven. You can add content without touching the code.

### Adding a New Yukkuri Type
1.  Open `data/yukkuri_types.yaml`.
2.  Add a new block with a unique key (e.g., `Alice`).
3.  Define stats like `base_health`, `color`, etc.

### Adding a New Item
1.  Open `data/items.yaml`.
2.  Add a new block.
3.  Define `cost`, `color`, and type-specific data (e.g., `nutrition` for food).

### Adding New AI Behaviors
1.  **Data**: Open `data/ai_actions.yaml`. Define the action, its type, and Utility Curves (Considerations).
2.  **Code** (If new logic is needed):
    *   If it's a generic interaction, existing logic might work.
    *   If it requires new mechanics (e.g., "Flying"), implement `execute_fly` in `src/ai/actions.py`.
