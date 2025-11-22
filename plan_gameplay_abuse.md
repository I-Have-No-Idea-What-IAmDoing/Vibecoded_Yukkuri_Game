# Gameplay: Abuse & Punishment Mechanics

## 1. Overview
This plan implements "Discipline" mechanics to the game. This includes adding a "Discipline" stat to Yukkuris and a "Punish" tool (Hit) for the player to enforce behavior. Punishment will lower happiness and health but increase discipline.

## 2. Data Model Changes
*   **File**: `src/yukkuri_game/game/yukkuri_components.py`
    *   **Action**: Modify `YukkuriStats` dataclass.
    *   **Detail**: Add `discipline: float = 0.0` (Range 0-100).

## 3. Input System Updates
*   **File**: `src/yukkuri_game/game/services.py` (`InputService`)
    *   **Action**: Add `start_punishing()` and `stop_punishing()` methods.
    *   **Action**: Add `_punishing_mode` boolean flag.
    *   **Action**: Add `is_punishing` property.

*   **File**: `src/yukkuri_game/game/input_system.py`
    *   **Action**: Subscribe to a new `PunishToolRequestedEvent`.
    *   **Action**: In `handle_event` (MOUSEBUTTONDOWN), check if `input_service.is_punishing` is true.
    *   **Action**: Implement `_handle_punishment(world, wx, wy)` logic.
        *   Find entity under cursor (Reuse hover logic or similar to cleaning).
        *   If entity is Yukkuri:
            *   Apply "Punish" effect.

*   **File**: `src/yukkuri_game/game/events.py`
    *   **Action**: Define `PunishToolRequestedEvent`.

## 4. Game Logic Implementation
*   **File**: `src/yukkuri_game/game/systems/interaction_system.py` (or `GameService` if refactoring not complete)
    *   **Action**: Implement `apply_punishment(entity_id)`.
    *   **Logic**:
        *   Decrease `health` (e.g., -10).
        *   Decrease `happiness` (e.g., -20).
        *   Increase `discipline` (e.g., +10).
        *   Play "hit" sound.
        *   Trigger "Crying" or "Damage" animation/state (optional/future).

## 5. UI Updates
*   **File**: `src/yukkuri_game/game/ui/hud.py`
    *   **Action**: Add a button for the "Punish" tool (e.g., a Gavel icon or "Hit" text).
    *   **Action**: Emit `PunishToolRequestedEvent` when clicked.

## 6. Pre-commit Steps
*   **Action**: Ensure proper testing, verification, review, and reflection are done.

## 7. Verification
*   **Test**: Create a test case where a Yukkuri is spawned, the punish tool is used, and verify stats (Health down, Happiness down, Discipline up).
