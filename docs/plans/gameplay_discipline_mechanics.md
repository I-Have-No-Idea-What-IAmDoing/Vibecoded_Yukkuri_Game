# Gameplay: Abuse & Punishment Mechanics

## Goal
Add "Discipline" mechanics to the game. This introduces a "Hit/Punish" tool that interacts with Yukkuris, modifying their happiness, health, and behavior probability. It provides a negative reinforcement loop for the AI.

## Steps

1.  **Update `YukkuriStats` Component**
    -   **File**: `src/yukkuri_game/game/yukkuri_components.py`
    -   Add a `discipline` (float, 0-100) field to `YukkuriStats`.
    -   Initialize it in `EntityFactory` (`src/yukkuri_game/game/entity_factory.py`).

2.  **Implement Discipline/Punish Logic in `GameService` or `InteractionSystem`**
    -   **File**: `src/yukkuri_game/game/services.py` (or new `interaction_system.py` if refactoring is done first, but I will assume `GameService` for now to be safe, or create a dedicated helper).
    -   Create a method `apply_punishment(entity_id, severity=10)`.
    -   Logic:
        -   Decrease `health` slightly (e.g., -5).
        -   Decrease `happiness` significantly (e.g., -20).
        -   Increase `discipline` (e.g., +15).
        -   Clamp values between 0-100.
        -   Trigger "Cry" or "Damage" sound.
        -   Trigger a visual effect (flash red or shake - optional/future).

3.  **Add "Punish" Tool to Input System**
    -   **File**: `src/yukkuri_game/game/services.py` (`InputService`)
    -   Add a `start_punishing()` method in `InputService` similar to `start_cleaning()`.
    -   **File**: `src/yukkuri_game/game/input_system.py`
    -   In `_handle_cleaning` (or a new `_handle_punishing`), detect clicks on Yukkuris.
    -   If clicked, call `apply_punishment`.

4.  **Update AI to Respect Discipline**
    -   **File**: `src/yukkuri_game/game/ai/utility.py`
    -   Modify utility calculations for "Bad" behaviors (e.g., eating poop, fighting).
    -   If `discipline` is high, reduce the utility score of these actions.
    -   Example: `utility = base_utility * (1.0 - (discipline / 100.0))`.

5.  **Update UI**
    -   **File**: `src/yukkuri_game/game/ui/hud_layout.py`
    -   Add a "Punish" button to the toolbar.
    -   Connect it to `InputService.start_punishing()`.

6.  **Verification**
    -   **Test**: Create a test in `tests/test_gameplay.py` (or similar).
    -   Spawn a Yukkuri.
    -   Apply punishment.
    -   Assert `discipline` increased, `happiness` decreased.
    -   Assert "Bad Behavior" utility is lower than before punishment.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
