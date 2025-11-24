# Actionable Tasks for Automated Headless Testing

## Phase 1: Foundation

- [ ] **Task 1: Create `HeadlessRunner` Class**
    - Create a new file `src/yukkuri_game/testing/runner.py`.
    - Implement a class that sets `SDL_VIDEODRIVER=dummy` before init.
    - Instantiate `YukkuriGame` with `headless=True`.
    - Add a `run_for(seconds: float)` method that pumps the loop.

- [ ] **Task 2: CLI Entry Point**
    - Modify `main.py` or add a new entry point (e.g., `test_runner.py`) to accept a scenario file.
    - `python -m yukkuri_game.testing.runner --scenario scenarios/basic_test.json`

## Phase 2: Input Simulation

- [ ] **Task 3: Event Injector**
    - Implement a system to parse JSON events and convert them to `pygame.event.Event`.
    - Map string event types ("MOUSEBUTTONDOWN", "KEYDOWN") to Pygame constants.
    - Handle coordinate mapping (if needed, though screen coords usually suffice).

- [ ] **Task 4: Scenario Loader**
    - Define the JSON schema for scenarios.
    - Create a `ScenarioLoader` that parses the JSON and queues events by timestamp.

## Phase 3: Integration & Verification

- [ ] **Task 5: Screenshot Integration**
    - Add a "SCREENSHOT" event type to the scenario loader.
    - When triggered, call `game.take_screenshot()` with a specific filename (defined in the scenario).

- [ ] **Task 6: Basic Smoke Test Scenario**
    - Create `tests/headless/scenarios/smoke_test.json`.
    - Actions: Wait 1s, Click (place yukkuri), Wait 2s, Screenshot, Exit.
    - Verify the screenshot is created.

## Phase 4: CI/CD & refinement

- [ ] **Task 7: Pytest Integration**
    - Create a pytest fixture that spins up the `HeadlessRunner`.
    - Allow writing tests in Python that programmatically queue events instead of using JSON.

- [ ] **Task 8: Documentation**
    - Update `README.md` or `AGENTS.md` with instructions on how to run headless tests and record new scenarios.
