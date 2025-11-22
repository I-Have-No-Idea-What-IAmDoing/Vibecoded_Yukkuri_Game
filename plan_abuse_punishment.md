# Plan: Gameplay - Abuse & Punishment Mechanics

## 1. Update Yukkuri Stats
*   **Target File**: `src/yukkuri_game/game/yukkuri_components.py`
*   **Action**: Modify `YukkuriStats` dataclass.
*   **Details**:
    *   Add `discipline: float = 0.0` (Range 0-100).
    *   Add documentation for the new field.

## 2. Implement Punish Tool in Input System
*   **Target File**: `src/yukkuri_game/game/services.py` (InputService)
*   **Action**: Add punishment mode methods.
*   **Details**:
    *   Add `start_punishing()` method.
    *   Add `stop_punishing()` method.
    *   Add `is_punishing` property.
    *   Ensure it's mutually exclusive with `placement` and `cleaning` modes.

*   **Target File**: `src/yukkuri_game/game/events.py`
*   **Action**: Add `PunishToolRequestedEvent`.

*   **Target File**: `src/yukkuri_game/game/input_system.py`
*   **Action**: Handle punishment input.
*   **Details**:
    *   Subscribe to `PunishToolRequestedEvent`.
    *   In `handle_event` (Mouse Left Click), if `is_punishing` is true:
        *   Detect clicked entity (similar to `_handle_cleaning` or `_handle_selection`).
        *   If a Yukkuri is clicked, trigger the punishment logic.
        *   Play a "hit" sound (e.g., using a placeholder sound or existing one).

## 3. Implement Punishment Logic
*   **Target File**: `src/yukkuri_game/game/services.py` (GameService) or `src/yukkuri_game/game/systems/interaction.py` (if refactored)
*   **Action**: Add `punish_entity` method.
*   **Details**:
    *   Input: `target_id`.
    *   Logic:
        *   Get `YukkuriStats`.
        *   Decrease `happiness` (e.g., -20).
        *   Decrease `health` (e.g., -5).
        *   Increase `discipline` (e.g., +10).
        *   Clamp values to 0-100.
        *   (Optional) Interrupt current AI action by clearing `AIState.current_action` or setting it to "Idle"/"Cry" (if "Cry" exists, otherwise just Idle/Stunned).

## 4. Integrate with AI (Optional but recommended)
*   **Target File**: `src/yukkuri_game/game/ai/utility.py` (Actions)
*   **Action**: Update weights based on discipline?
*   **Details**:
    *   This might be complex for this task alone. For now, the stats update is sufficient.
    *   Future consideration: High discipline reduces probability of "Bad Behavior" (like eating poop, if that behavior exists).

## 5. Pre-commit Steps
*   **Action**: proper testing, verification, review, and reflection.
*   **Details**: Ensure the new stats are saved/loaded correctly (check `PersistenceService` in `services.py`). Verify the tool toggles correctly.
