# Actionable Tasks for Proposal 4

1.  **Core Infrastructure**
    - [ ] Create `src/yukkuri_game/testing/` directory.
    - [ ] Implement `HeadlessGame` class inheriting from `YukkuriGame`.
        - [ ] Override `__init__` to set `SDL_VIDEODRIVER=dummy`.
        - [ ] Implement the fixed-timestep loop.
        - [ ] Add `scenario` injection mechanism.

2.  **Input & Determinism Utilities**
    - [ ] Add explicit seeding helper: `set_deterministic_seed(seed)`.
    - [ ] Create `InputProxy` class to simplify input injection (e.g., `game.test_input.click(x, y)`).

3.  **Scenario Runner Integration**
    - [ ] Create a `run_scenario(scenario_func)` helper function.
    - [ ] Integrate with `pytest`. Create a `conftest.py` fixture `headless_game` that yields a factory for games.

4.  **Proof of Concept Scenario**
    - [ ] Write `tests/system/test_spawn_logic.py`.
    - [ ] Define a scenario that spawns a unit and asserts its existence.
    - [ ] Run via `pytest`.

5.  **Visual Debugging Support**
    - [ ] Implement `game.take_screenshot(name)` method in `HeadlessGame`.
    - [ ] Ensure screenshots are saved to `tests/artifacts/` for review on failure.
