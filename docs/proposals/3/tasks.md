# Implementation Tasks

This document outlines the actionable tasks required to implement the Automated Headless Testing system described in `design.md`.

## Phase 1: Foundation (Headless Support)

- [ ] **Add CLI Argument Parsing**
    - Modify `src/yukkuri_game/main.py` (or entry point) to accept `--headless`, `--test-duration`, and `--screenshot-interval`.
    - Use `argparse` to handle these arguments.
- [ ] **Implement Headless Initialization**
    - In `YukkuriGame.__init__` or `main.py`, check for `--headless`.
    - If true, set `os.environ["SDL_VIDEODRIVER"] = "dummy"` *before* `pygame.init()`.
    - Ensure window mode flags are compatible with dummy driver (e.g., avoid `OPENGL` if problematic, though usually fine).
- [ ] **Implement Auto-Shutdown**
    - Add logic in the main game loop to check `time.time() - start_time > duration`.
    - If duration exceeded, trigger graceful shutdown (`running = False`).

## Phase 2: Input Automation

- [ ] **Create `TestAgent` Class**
    - Location: `src/yukkuri_game/utils/test_agent.py` (or similar).
    - Functionality: Methods to create and post `pygame.event.Event`.
        - `mouse_move(pos)`
        - `mouse_click(pos, button)`
        - `key_press(key)`
- [ ] **Implement Scenario Loader**
    - Define a simple interface for running a test scenario.
    - Example: A class `TestScenario` with a `run(game_instance)` method that gets called every frame (or via a coroutine).

## Phase 3: Verification & Determinism

- [ ] **Implement Screenshot Scheduler**
    - Add logic to `YukkuriGame` to take screenshots at intervals defined by CLI args.
    - Ensure output directory exists (`tests/results/...`).
- [ ] **Implement Fixed Time Step (Optional but Recommended)**
    - Add a `--fixed-dt` flag.
    - If enabled, ignore `clock.tick()` return value and force `dt = 1/60.0` passed to `update()`.

## Phase 4: Integration & CI

- [ ] **Create Example Scenario**
    - Create `tests/scenarios/basic_headless.py`.
    - Script: Start game, wait 2 seconds, click a button (if GUI exists) or place unit, wait 2 seconds, exit.
- [ ] **Add Pytest Integration**
    - Create a `pytest` fixture or test wrapper that invokes the game in a subprocess or strictly controlled thread (subprocess preferred for clean global state) with the headless flags.
    - Example: `tests/system/test_headless_run.py`.

## Estimated Effort
- Phase 1: 1-2 hours
- Phase 2: 3-4 hours
- Phase 3: 2 hours
- Phase 4: 2 hours
