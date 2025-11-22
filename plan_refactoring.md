# Technical: Code Refactoring

## 1. Overview
This plan focuses on decoupling the `GameService` god-object and removing rendering logic from `InputSystem`.

## 2. Refactor GameService
*   **File**: `src/yukkuri_game/game/services.py`
    *   **Action**: Identify interaction logic (`find_best_item`, `interact_with_item`).
*   **File**: `src/yukkuri_game/game/systems/interaction.py` (New File)
    *   **Action**: Create `InteractionSystem`.
    *   **Action**: Move `find_best_item` and `interact_with_item` logic here.
    *   **Action**: Ensure `InteractionSystem` is registered in `ServiceLocator` or World.
*   **File**: `src/yukkuri_game/game/ai/behavior.py`
    *   **Action**: Update references from `GameService` to `InteractionSystem`.

## 3. Refactor InputSystem
*   **File**: `src/yukkuri_game/game/input_system.py`
    *   **Action**: The current `InputSystem` updates `self.input_service.selection_rect` which is a `pygame.Rect`.
    *   **Action**: The task states "InputSystem doesn't handle rendering logic".
    *   **Observation**: `InputSystem` currently *calculates* the rect but doesn't draw it. `Yukkurrium` or UI likely draws it.
    *   **Refinement**: If `InputSystem` calculates the rect in *screen coordinates*, it is somewhat tied to rendering. It should ideally track world coordinates.
    *   **Plan**:
        *   Ensure `InputService` stores selection in World Coordinates (start/end points).
        *   Let the UI/Renderer calculate the Screen Rect for drawing.
        *   However, if `selection_rect` is used purely for drawing the box overlay, `InputSystem` calculating it based on mouse pos is acceptable *input handling* (converting input to visual feedback data).
        *   If `InputSystem` contains actual `pygame.draw` calls (checked: it does not), it is already partially decoupled.
        *   I will verify if `InputSystem` does any coordinate transformation that belongs in the renderer.
        *   Current `InputSystem`: `self.yukkurrium.world_to_screen(...)`. This coupling to `yukkurrium` for screen conversion is the issue.
        *   **Solution**: `InputSystem` should operate in World Coordinates (via `Camera` service if exists, or passed view matrix). It should not depend on `Yukkurrium` class directly if possible.
        *   For now, I will extract `InteractionSystem` as the primary goal. The `InputSystem` refactoring might require a `CameraService` to fully decouple from `Yukkurrium`.

## 4. Pre-commit Steps
*   **Action**: Ensure proper testing, verification, review, and reflection are done.

## 5. Verification
*   **Test**: Run existing tests (`test_services.py`, `test_utility_ai.py`) to ensure no regressions in interaction logic.
