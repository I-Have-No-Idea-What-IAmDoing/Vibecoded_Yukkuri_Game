# Fix AI State Persistence

## Goal
Ensure that AI state (current action, target, internal data) is saved and loaded correctly, preventing "amnesia" upon reloading a save.

## Steps

1.  **Update `PersistenceService.save_game`**
    -   **File**: `src/yukkuri_game/game/services.py`
    -   Inside the entity loop, fetch `AIState` component.
    -   Serialize:
        -   `current_action` (str)
        -   `current_target_id` (int)
        -   `state_data` (dict)
        -   `path` (list of tuples - optional but recommended)
    -   Add this to the entity data dictionary under key `"ai_state"`.

2.  **Update `PersistenceService.load_game`**
    -   **File**: `src/yukkuri_game/game/services.py`
    -   Inside the entity creation loop:
        -   Check for `"ai_state"` key.
        -   If present, get `AIState` component from the newly created entity.
        -   Restore `current_action`, `current_target_id`, `state_data`, `path`.
        -   *Crucial*: `current_target_id` refers to an Entity ID. Entity IDs might change upon reload if not handled carefully.
        -   *Strategy*:
            -   Option A: Save/Load strict Entity IDs. This requires `EntityFactory` to allow specifying ID or `World` to force IDs. (Hard in `esper` typically).
            -   Option B: Map old IDs to new IDs.
                -   First pass: Create all entities and store mapping `old_id -> new_id`.
                -   Second pass: Restore references (like `current_target_id`) using the map.
    -   **Refinement**: `PersistenceService.load_game` currently creates entities one by one. I need to change it to a two-pass approach or use a mapping.
        -   Pass 1: Create all entities, store `old_id` (from save) -> `new_id` (from factory) in a dict.
        -   Pass 2: Loop through saved data again to restore `AIState`, mapping the `current_target_id`.

3.  **Verification**
    -   **Test**: `tests/test_persistence_ai.py` (Create new test file).
    -   Scenario:
        -   Create Yukkuri A and Item B.
        -   Set Yukkuri A target to Item B.
        -   Save Game.
        -   Clear World.
        -   Load Game.
        -   Assert Yukkuri A exists, Item B exists.
        -   Assert Yukkuri A `current_target_id` points to the *new* ID of Item B.
        -   Assert Yukkuri A `current_action` is preserved.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
