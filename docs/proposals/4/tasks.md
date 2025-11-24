# Actionable Tasks for Proposal 4 (Revised)

1.  **Core Infrastructure**
    - [ ] Create `src/yukkuri_game/testing/` directory.
    - [ ] Refactor `YukkuriGame` to expose a `tick(dt)` method (separating logic from the `while` loop).
    - [ ] Create `TestEnvironment` context manager (handles `SDL_VIDEODRIVER`, `SDL_AUDIODRIVER`).
    - [ ] Implement `GameDriver` class (Composition based).
        - [ ] Takes `YukkuriGame` instance as dependency.
        - [ ] Implements the fixed-timestep loop manually.
        - [ ] Handles generator iteration and exception catching.

2.  **Input & Determinism Utilities**
    - [ ] Add explicit seeding helper in `GameDriver`: `seed_rng(seed)`.
    - [ ] Implement `InputHelper` functions that wrap `pygame.event.post`:
        - [ ] `post_click(x, y)`
        - [ ] `post_key_down(key)`, `post_key_up(key)`

3.  **Scenario Runner Integration**
    - [ ] Define Predicate classes/functions: `WaitUntil(predicate)`, `WaitFrames(n)`.
    - [ ] Create a `run_scenario(game, scenario_gen)` helper.
    - [ ] Integrate with `pytest`. Create a `conftest.py` fixture `game_driver` that yields a driver with a fresh game instance.

4.  **Proof of Concept Scenario**
    - [ ] Write `tests/system/test_spawn_logic.py`.
    - [ ] Define a scenario generator using `yield` and predicates.
    - [ ] Run via `pytest`.

5.  **Visual Debugging Support**
    - [ ] Implement `driver.save_screenshot(filename)` using `game.render()`.
    - [ ] Integrate with `pytest-regressions` or similar for Golden Image management (optional for Phase 1).
    - [ ] Configure driver to save screenshot on assertion failure.
