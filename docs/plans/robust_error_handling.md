# Robust Error Handling in Loop

## Goal
Prevent the entire game from crashing due to a single exception in the update loop (e.g., AI logic error).

## Steps

1.  **Wrap Update Loop**
    -   **File**: `src/yukkuri_game/main.py` (or `engine/core.py` where the main loop is).
    -   Locate `self.world.process()` or similar update call.
    -   Wrap in `try...except Exception as e`.

2.  **Log and Notify**
    -   **File**: `src/yukkuri_game/main.py`
    -   In `except` block:
        -   `logger.exception("Game Loop Error")`
        -   Call `HudRenderer.show_error(str(e))` (if accessible).
        -   *Optionally*: Pause the game (`time_scale = 0`) to prevent spamming the error 60 times a second.

3.  **Verification**
    -   **Test**: Inject a temporary bug (e.g., `raise ValueError("Test")` in an AI action).
    -   Run game.
    -   Verify game doesn't close.
    -   Verify error is logged and/or displayed.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
