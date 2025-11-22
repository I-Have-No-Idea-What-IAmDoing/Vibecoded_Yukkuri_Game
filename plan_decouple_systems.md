# Plan: Decouple Systems

This plan addresses the issue of `GameService` becoming a god-object and `InputSystem` handling rendering logic.

## 1. Move Interaction Logic to `InteractionSystem`

### 1.1 Create `InteractionSystem`
- Create `src/yukkuri_game/game/systems/interaction_system.py`.
- This system will be responsible for processing interaction requests (e.g. eating, sleeping).
- It will inherit from `System`.
- It will need access to `World`, `AudioManager`, `EventBus`.

### 1.2 Define `InteractionRequest` Component
- In `src/yukkuri_game/game/components.py` (or `yukkuri_components.py`), add a new component `InteractionRequest`.
    - Attributes:
        - `target_id`: int
        - `consume`: bool (defaults to True)
        - `interaction_type`: str (optional, for future extensibility e.g. "EAT", "SLEEP", "PLAY")

### 1.3 Migrate Logic from `GameService`
- Move `interact_with_item` logic from `GameService` to `InteractionSystem.update` (or a helper method called by update).
- The system will iterate over entities with `InteractionRequest` component.
- For each entity:
    - Perform the interaction logic (check distance, apply stats changes, play sound, destroy item if consume=True).
    - Remove the `InteractionRequest` component.
- Remove `interact_with_item` from `GameService`.

### 1.4 Update Behavior Tree Actions
- Modify `Interact` action in `src/yukkuri_game/game/ai/behavior.py`.
- Instead of calling `game_service.interact_with_item`, it should add an `InteractionRequest` component to the entity.
- Ensure `Interact` action handles the status correctly (e.g. return SUCCESS immediately if request added, or wait? Since BT runs every frame, maybe return RUNNING until `InteractionRequest` is removed? Or just SUCCESS assuming system picks it up next frame).
    - *Decision*: Return SUCCESS. The action's job is to *initiate* the interaction. The system handles the result. If we need to wait for animation, that's a different state. For now, instant success is fine.

### 1.5 Register System
- Register `InteractionSystem` in `Yukkurrium` or wherever systems are added to the world.

## 2. Decouple Rendering from `InputSystem`

### 2.1 Refactor `InputService`
- Modify `src/yukkuri_game/game/services.py`.
- Remove `selection_rect` (which was a `pygame.Rect`).
- Add `drag_start_pos` (tuple[float, float] or [int, int] - screen coords) and `drag_current_pos` (screen coords).
- Add `is_dragging` boolean property.

### 2.2 Update `InputSystem`
- In `src/yukkuri_game/game/input_system.py`:
    - In `handle_event`:
        - On `MOUSEBUTTONDOWN`: Set `input_service.drag_start_pos` and `input_service.is_dragging = True`.
        - On `MOUSEMOTION`: Update `input_service.drag_current_pos`.
        - On `MOUSEBUTTONUP`: Set `input_service.is_dragging = False`.
    - Remove code that calculates `pygame.Rect` directly.

### 2.3 Update `HudRenderer`
- In `src/yukkuri_game/game/ui/hud_renderer.py`:
    - In `update` (or a new method `_draw_selection_box`):
        - Check `input_service.is_dragging`.
        - If true, get start and current pos from `input_service`.
        - Calculate the `pygame.Rect` for the selection box.
        - Draw the rect (using `pygame.draw.rect` on the screen surface - might need to pass surface to `HudRenderer.update` or access it via `pygame.display.get_surface()`).
        - Currently `HudRenderer` manages UI elements. Drawing a raw rect might be outside its typical `pygame_gui` scope but it's the right place for HUD overlays.
        - Alternatively, use a `UISelectionBox` element if one exists or create a temporary panel. But raw drawing is faster/easier for a selection box.

## 3. Verification
- Run tests to ensure interactions (eating, sleeping) still work.
- Manually verify selection box drawing works and feels responsive.
- Run linting/static analysis.

## 4. Pre-commit
- Ensure proper testing, verification, review, and reflection are done.
