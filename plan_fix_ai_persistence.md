# Fix AI State Persistence (Data Integrity)

## 1. Overview
This plan addresses the "amnesia" bug where AI state is lost upon loading a save game. It involves serializing and deserializing the `AIState` component in `PersistenceService`.

## 2. Data Model Analysis
*   **Component**: `AIState` (in `src/yukkuri_game/game/yukkuri_components.py`)
    *   `current_action`: str
    *   `current_target_id`: int
    *   `path`: list (Optional, maybe skip or simplify)
    *   `action_progress`: float
    *   `state_data`: Dict

## 3. Implementation Steps
*   **File**: `src/yukkuri_game/game/services.py` (`PersistenceService`)
    *   **Method**: `save_game`
        *   **Action**: Inside the entity loop, check for `AIState` component.
        *   **Action**: If present, add "ai_state" block to `ent_data`.
        *   **Fields**:
            *   `current_action`
            *   `current_target_id`
            *   `action_progress`
            *   `state_data` (JSON serializable dict)
    *   **Method**: `load_game`
        *   **Action**: Inside the entity creation loop, check for "ai_state" in `ent_data`.
        *   **Action**: If present, get `AIState` component (add if missing, though `EntityFactory` likely adds it for Yukkuris).
        *   **Action**: Restore fields.

## 4. Testing & Verification
*   **File**: `tests/game/test_persistence_economy.py`
    *   **Action**: Create a new test method `test_ai_state_persistence`.
    *   **Steps**:
        1.  Create World and Services.
        2.  Create a Yukkuri.
        3.  Set `AIState` manually (e.g., Action="Eat", Target=123, Data={'foo': 'bar'}).
        4.  Save Game.
        5.  Clear World.
        6.  Load Game.
        7.  Retrieve Yukkuri.
        8.  Assert `AIState` matches saved values.

## 5. Pre-commit Steps
*   **Action**: Ensure proper testing, verification, review, and reflection are done.
