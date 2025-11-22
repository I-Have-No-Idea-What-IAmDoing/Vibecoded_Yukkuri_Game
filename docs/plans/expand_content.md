# Expand Content (Data)

## Goal
Add more variety to the game by introducing new Yukkuri types and Items.

## Steps

1.  **Add New Yukkuri Types**
    -   **File**: `data/yukkuris/types.toml`
    -   Add `[yukkuris.alice]`
        -   Stats: High Intelligence (if applicable), standard health.
    -   Add `[yukkuris.chen]`
        -   Stats: High Speed, lower health.

2.  **Add New Items**
    -   **File**: `data/items/items.toml`
    -   Add `[items.poop_stick]` (if implementing discipline tool as item, or just "Stick").
    -   Add `[items.orange_juice]` (High nutrition, low cost).
    -   Add `[items.shiny_thing]` (High fun).

3.  **Ensure Assets Load**
    -   **File**: `src/yukkuri_game/engine/resource_manager.py`
    -   Verify that adding keys to TOML is sufficient. (Usually yes, if assets exist).
    -   **Asset Creation**: Since I cannot create images, I will use placeholders or reuse existing images (e.g., tinting them programmatically if possible, or just mapping to existing PNGs for now).
    -   *Note*: If images are missing, the game might crash or show pink squares. I should map them to `reimu.png` / `cookie.png` temporarily in the TOML if real assets aren't available.

4.  **Verification**
    -   **Manual**: Run game. Check "Place" menu.
    -   Verify new buttons appear.
    -   Spawn them. Verify stats match TOML.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
