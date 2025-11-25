# Implementation Plan: Visual Hopping for Yukkuri Movement

This plan details the steps to implement the purely visual hopping effect as described in `design.md`. The core principle is to separate the visual representation of movement (the "view") from the underlying physics simulation (the "model").

## Phase 1: The Visual Bob Component and System

1.  [ ] **Define `VisualBob` Component**
    -   Create the `VisualBob` dataclass in a suitable components file (e.g., `src/yukkuri_game/game/components.py`).
    -   Fields: `timer: float`, `bob_height: float`, `bob_speed: float`.
    -   *Verification*: The component can be added to an entity and initialized with default values.

2.  [ ] **Update Entity Factory**
    -   Modify the `YukkuriFactory` to attach the `VisualBob` component to all new Yukkuri entities.

3.  [ ] **Create `VisualBobSystem`**
    -   Create a new system in `src/yukkuri_game/game/systems/visual_bob_system.py`.
    -   The system's `update` method will iterate through all entities with a `VisualBob` component and a physics body.
    -   **Logic**:
        -   If the entity's physics body has a velocity greater than a small threshold, increment the `VisualBob.timer`.
        -   If the entity is stationary, reset the `VisualBob.timer` to `0`.
    -   Register the `VisualBobSystem` in the main game loop to run on every frame.

## Phase 2: Rendering Integration

4.  [ ] **Modify the Rendering System**
    -   Locate the primary rendering logic (e.g., `RenderSystem`).
    -   Before rendering an entity's sprite, check if it has a `VisualBob` component.
    -   If it does, calculate the vertical offset using the formula from the design: `offset_y = abs(sin(bob.timer * bob.bob_speed)) * bob.bob_height`.
    -   Draw the sprite at `(model_x, model_y - offset_y)`.
    -   Crucially, the entity's actual `y` position (the model) is not changed. This ensures collision detection and physics are unaffected.
    -   (Optional) Draw a simple shadow sprite at the entity's true `(model_x, model_y)` to enhance the illusion of height.

## Phase 3: Animation Triggers

5.  [ ] **Implement State Change Detection for Animations**
    -   A system or manager needs to track the movement state (`is_moving`). This might require adding a simple `MovementState` component.
    -   When an entity's state changes from `stopped` to `moving`, trigger a "prepare to move" (squash) animation.
    -   When the state changes from `moving` to `stopped`, trigger a "landing" animation and emit dust particles at the entity's true position.

6.  [ ] **Refine AI Actions**
    -   The AI actions like `MoveToTarget` do not need to change how they command the entity to move. They still set velocity or use the `MovementController`.
    -   The animation triggers should be driven by the *result* of these actions (the entity moving or stopping), not by the AI's intent.

## Phase 4: Tuning and Verification

7.  [ ] **Expose Tuning Parameters**
    -   Ensure `bob_height` and `bob_speed` are easily configurable, perhaps in a central configuration file or directly on the Yukkuri prefabs, so they can be tweaked by designers without code changes.

8.  [ ] **Testing**
    -   Playtest to confirm the visual bobbing is smooth and aesthetically pleasing.
    -   Verify that the bobbing effect does *not* affect collision detection, AI targeting, or physics interactions in any way. The entity's collision shape should remain firmly on the ground.
    -   Ensure the landing/takeoff animations and effects trigger reliably.
