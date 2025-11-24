# Actionable Tasks for Automated Headless Testing

1.  **Prototype Headless Screenshotting**
    - [ ] Create a script `scripts/test_headless_render.py` that initializes Pygame with `SDL_VIDEODRIVER=dummy`.
    - [ ] Create a surface, draw something to it.
    - [ ] Save it as an image.
    - [ ] Verify this works without a display.

2.  **Refactor `GameLoop` / `YukkuriGame` for Offscreen Rendering**
    - [ ] Modify `GameLoop.__init__` or `setup` to handle a "test mode" or "offscreen mode".
    - [ ] If headless, create a `pygame.Surface((width, height))` instead of `pygame.display.set_mode`.
    - [ ] Ensure `RenderSystem` and UI draw to this surface.
    - [ ] Update `draw()` to flip/update only if not truly headless, or just update the surface.

3.  **Implement `TestScenario` and `InputInjector`**
    - [ ] Create `src/yukkuri_game/testing/` module.
    - [ ] Implement `InputInjector` class that can post Pygame events.
    - [ ] Implement `TestScenario` class that holds a timeline of events.

4.  **Create `HeadlessGameRunner`**
    - [ ] Create a class that inherits from or wraps `YukkuriGame`.
    - [ ] Overrides `update()` to check the scenario and inject events.
    - [ ] handles automatic termination.

5.  **Write a Sample Test Scenario**
    - [ ] Create a test that starts the game.
    - [ ] Spawns a Yukkuri (simulates clicking button).
    - [ ] Waits 5 seconds.
    - [ ] Takes a screenshot.
    - [ ] Exits.

6.  **Integration with Pytest**
    - [ ] Add a new test file `tests/system/test_headless_scenarios.py`.
    - [ ] Run the sample scenario.
    - [ ] Verify screenshot exists.
