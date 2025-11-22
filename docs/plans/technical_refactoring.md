# Technical: Code Refactoring (Decouple Systems)

## Goal
Refactor `GameService` to reduce its "god object" status and decouple the `InputSystem` from rendering logic.

## Steps

1.  **Create `InteractionSystem`**
    -   **File**: Create `src/yukkuri_game/game/systems/interaction_system.py`.
    -   Move `interact_with_item` logic from `GameService` to this system (or a static helper/service).
    -   Move `find_best_item` logic here as well.
    -   Update `GameService` to delegate to `InteractionSystem` or remove the methods if `InteractionSystem` is accessed directly by AI (via ServiceLocator).

2.  **Refactor `InputSystem`**
    -   **File**: `src/yukkuri_game/game/input_system.py`
    -   Currently, `InputSystem` calculates selection rects and handles some UI-like logic (e.g., drag distance for rendering).
    -   Move purely visual calculations (like `selection_rect`) to `HudRenderer` or `InputService` (state only).
    -   Ensure `InputSystem` only handles *events* and updates *state* in `InputService`. `HudRenderer` should read `InputService` state to draw the box.
    -   *Current Check*: `InputSystem` sets `self.input_service.selection_rect`. This is actually okay (State Update). But it uses `pygame.Rect` directly. Ideally, it should store coordinates, and Renderer creates the Rect. But `pygame.Rect` is fine as a data structure.
    -   **Main Task**: Ensure `InputSystem` does not contain any rendering code (it seems it doesn't, it just updates state).
    -   **Refinement**: Move `screen_to_world` and `world_to_screen` calls to a shared utility or `Camera` service if they are duplicated, but they are in `Yukkurrium`.
    -   Double check `_handle_selection` complexity.

3.  **Update Imports**
    -   Search for usages of `GameService.interact_with_item` and update to use the new system.
    -   Files: `src/yukkuri_game/game/ai/behavior.py` (Interact action).

4.  **Verification**
    -   Run existing tests to ensure no regressions in interaction logic.
    -   Manual test: Eating, Sleeping should still work. Selection box should still appear.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
