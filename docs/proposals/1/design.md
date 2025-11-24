# Automated Headless Testing Design

## Problem Description
The current testing infrastructure primarily relies on unit tests (`tests/`) and manual testing. While there is a `--headless` mode, it is not fully utilized for automated integration/system testing where the game runs for a duration and verifies behavior. There is a need for a system that can run the game in a "real" environment (but headless), simulate human-like input, verify visual output via screenshots, and automatically terminate after a set duration or condition.

## Proposed Solution
We will implement an **Automated Headless Testing System** that extends the existing game loop to support:
1.  **Scripted Execution:** Ability to run the game with a pre-defined "test script" or "scenario".
2.  **Input Simulation:** A mechanism to inject input events (mouse clicks, key presses) programmatically, simulating a user.
3.  **Visual Verification:** Periodically taking screenshots or taking screenshots on specific events for regression testing.
4.  **Automatic Termination:** Stopping the game loop after a fixed duration or when a victory/failure condition is met.
5.  **Headless Rendering:** Ensuring that even in headless mode, a surface exists to draw to (even if not displayed) so screenshots can be captured.

## Design Details

### 1. Headless Rendering for Screenshots
Currently, `GameLoop` initializes `pygame.display.set_mode`. In headless mode (`--headless`), `draw()` is skipped. To support screenshots in headless mode:
- We must initialize a "virtual" screen surface even in headless mode.
- We can use `os.environ["SDL_VIDEODRIVER"] = "dummy"` before `pygame.init()` if truly headless (no X11/display), but this might affect `pygame.image.save`.
- Alternatively, we can just not call `pygame.display.set_mode` but create a `pygame.Surface` that acts as the screen, and have `RenderSystem` draw to that.
- `YukkuriGame` needs a slight refactor to allow `self.screen` to be an offscreen `pygame.Surface` when headless.

### 2. Test Runner & Controller
We will introduce a `HeadlessTestRunner` class (or similar) that wraps `YukkuriGame`.
- It will parse a "Scenario" or "Test Plan".
- It will hook into the `update()` loop or use a custom game loop to inject inputs at specific timestamps.

### 3. Input Simulation
We can use `pygame.fastevent.post()` or directly call `game.on_event()` with constructed `pygame.event.Event` objects.
A `InputScenario` class can define a list of actions:
```python
scenario = [
    {"time": 1.0, "action": "click", "pos": (100, 100), "button": 1},
    {"time": 2.0, "action": "key", "key": "F3"},
    {"time": 5.0, "action": "screenshot", "name": "initial_state"},
    {"time": 10.0, "action": "quit"}
]
```

### 4. Integration with Pytest
These headless tests should be runnable via `pytest`. We can create a pytest fixture that sets up the `YukkuriGame` in headless mode with a dummy video driver, runs a scenario, and asserts that screenshots match expected baselines (optional, or just that they exist) or that no exceptions occurred.

## Rationale
- **Realism:** Runs the actual game loop, systems, and logic, catching integration bugs that unit tests miss.
- **Visuals:** Screenshots allow verifying rendering artifacts or UI layouts without manual inspection every time.
- **Automation:** Can be run in CI/CD pipelines.

## Implementation Tasks
See `tasks.md` for the step-by-step implementation plan.
