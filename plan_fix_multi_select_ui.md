# Plan: Fix Multi-Select UI Feedback

This plan improves the UI feedback when multiple entities are selected.

## 1. Update `HudRenderer._update_stats_display`

- File: `src/yukkuri_game/game/ui/hud_renderer.py`
- Logic for `len(selected_entities) > 1`:
    - Initialize counters for `yukkuris` and `items`.
    - Initialize sums for `hunger`, `happiness`, `health`, `value`.
    - Iterate through `selected_entities`:
        - Resolve entity ID.
        - Check components (`YukkuriStats`, `ItemStats`).
        - Accumulate stats.
    - Calculate averages (divide by count).
    - Format the text string:
        - "Selected: X entities"
        - "Yukkuris: Y (Avg HP: A, Avg Hunger: B, Avg Happy: C)"
        - "Items: Z (Avg Value: V)"
    - Set `self.layout.info_label` text.

## 2. Update `HudLayout.create_selection_window`

- File: `src/yukkuri_game/game/ui/hud_layout.py`
- Ensure the buttons "Sell" and "Train" explicitly state "Sell All (X)" or similar if multiple are selected.
    - The code already has "Sell All" logic.
    - Enhancement: Add the count to the button text? e.g., "Sell All (5)".
    - Verify tooltips are accurate.

## 3. UX Tweaks
- Ensure the selection window resizes or scrolls if the summary is long (though summary should be concise).
- Bold key metrics.

## 4. Verification
- In-game test:
    - Spawn multiple Yukkuris.
    - Select one -> Check detailed view.
    - Drag select multiple -> Check summary view (Counts, Averages).
    - Select mix of Yukkuris and Items -> Check combined summary.

## 5. Pre-commit
- Ensure proper testing, verification, review, and reflection are done.
