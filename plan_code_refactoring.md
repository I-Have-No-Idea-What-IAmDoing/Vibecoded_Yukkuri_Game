# Plan: Technical - Code Refactoring

## 1. Create Interaction System
*   **Target File**: `src/yukkuri_game/game/systems/interaction.py` (New File)
*   **Action**: Define `InteractionSystem`.
*   **Details**:
    *   Move `find_best_item` logic from `GameService`.
    *   Move `interact_with_item` logic from `GameService`.
    *   Add `interact_with_entity` (from Social plan).
    *   This system can be a pure logic helper or an ECS System if it needs to process queues. For now, a Service or Helper class is fine to replace `GameService` methods. Let's keep it as a Service: `InteractionService`.
    *   Update `ServiceLocator` in `src/yukkuri_game/engine/service_locator.py` or registration in `main.py` (if applicable) to include `InteractionService`.

## 2. Refactor GameService
*   **Target File**: `src/yukkuri_game/game/services.py`
*   **Action**: Remove moved methods.
*   **Details**:
    *   Deprecate or remove `find_best_item` and `interact_with_item`.
    *   Update references in `behavior.py` (`Interact` and `FindItem` nodes) to use `InteractionService` instead of `GameService`.

## 3. Refactor InputSystem (Rendering)
*   **Target File**: `src/yukkuri_game/game/input_system.py`
*   **Action**: Remove rendering/rect calculations used for drawing.
*   **Details**:
    *   `InputSystem` should only handle events and update logical state (`start_pos`, `end_pos`, `selection_state`).
    *   It should NOT create `pygame.Rect` for the purpose of *drawing* inside the system (though it might need it for intersection checks).
    *   Currently, it updates `self.input_service.selection_rect`. This is fine as state, but `yukkurrium.py` likely reads this to draw.
    *   Verify where `selection_rect` is drawn. If `Yukkurrium` draws it, ensure `InputSystem` only provides the coordinates/state.
    *   Refactor `world_to_screen` calls: If `InputSystem` needs them for logic (selection box in world space vs screen space), that's valid. But if it's calculating purely for the UI layer, see if we can defer that.
    *   *Correction*: `InputSystem` calculates `selection_rect` which is a `pygame.Rect` (Screen Coordinates). This is "Rendering Logic" leaking into Input.
    *   **Change**: `InputSystem` should store `drag_start` and `drag_end` in *World Coordinates* (or keep screen coords as raw input data).
    *   The *Renderer* (Yukkurrium) should calculate the visual rect to draw based on those coordinates.

## 4. Update Yukkurrium (Rendering)
*   **Target File**: `src/yukkuri_game/game/yukkurrium.py`
*   **Action**: Update drawing logic.
*   **Details**:
    *   Read `drag_start` / `drag_end` from `InputSystem` (or `InputService`) to draw the selection box.
    *   Do not rely on `input_service.selection_rect` (screen rect) if possible, or ensure `InputSystem` calculates it solely for UI state, not drawing commands.

## 5. Pre-commit Steps
*   **Action**: proper testing, verification, review, and reflection.
*   **Details**: Ensure no cyclic dependencies are introduced. Verify that `GameService` is cleaner. Ensure selection box still works.
