# Fix Multi-Select UI Feedback

## Goal
Improve the UI feedback when multiple entities are selected. Instead of just a count, show average stats and a breakdown of types.

## Steps

1.  **Update `HudRenderer._update_stats_display`**
    -   **File**: `src/yukkuri_game/game/ui/hud_renderer.py`
    -   Logic:
        -   Iterate through `selected_entities`.
        -   Group by type (Reimu, Marisa, Item types).
        -   Calculate Sum and Count for stats (Health, Happiness, Hunger).
    -   Formatting:
        -   Display counts per type: "3 Reimus, 2 Marisas".
        -   Display Averages:
            -   "Avg HP: X"
            -   "Avg Happiness: Y"
            -   "Avg Hunger: Z"
    -   Update `info_label` text with this formatted string.

2.  **Update `HudLayout` for Bulk Actions**
    -   **File**: `src/yukkuri_game/game/ui/hud_layout.py`
    -   Check the logic for the "Sell" or "Train" buttons (if they exist, or add them).
    -   Ensure the button label updates if selection > 1 (e.g., "Sell Selected (5)").

3.  **Verification**
    -   **Manual**: Run game. Spawn 3 Yukkuris with different stats.
    -   Select all 3.
    -   Verify the Info Window shows the correct averages and counts.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
