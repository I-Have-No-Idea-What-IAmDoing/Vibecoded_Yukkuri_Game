# Headless Testing System

The Headless Testing System provides a way to run the full game loop without a graphical window or audio device. It is designed for deterministic, automated integration testing, allowing you to simulate user inputs, verify game state, and even take screenshots in a CI/CD environment.

## Overview

Traditional game testing often involves unit tests for individual components (like ECS systems) and manual playtesting for the full experience. The Headless Testing System bridges this gap by allowing you to:

*   **Run the full game loop**: This includes ECS updates, input handling, and game logic.
*   **Inject Inputs**: Simulate mouse clicks and key presses programmatically.
*   **Deterministic Execution**: Control the random seed and time steps for reproducible results.
*   **Fast Execution**: Run simulations faster than real-time (no rendering overhead, unless requested).
*   **Visual Verification**: Take screenshots at any point to verify rendering correctness or capture failure states.

## Architecture

The system consists of three main components located in `src/yukkuri_game/testing/`:

1.  **`GameDriver` (`src/yukkuri_game/testing/driver.py`)**:
    *   The core controller that wraps a `YukkuriGame` instance.
    *   It manages the game loop tick-by-tick using a fixed time step (`fixed_dt`).
    *   It executes "Scenarios" (test scripts) defined as Python generators.
    *   It handles input injection and screenshots.

2.  **`test_environment` (`src/yukkuri_game/testing/environment.py`)**:
    *   A context manager that configures the environment variables (`SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`) to prevent Pygame from trying to open real windows or audio devices.
    *   This is crucial for running tests on servers or CI runners.

3.  **Headless Support in `YukkuriGame`**:
    *   The `YukkuriGame` class (and its parent `GameLoop`) accepts a `headless=True` flag.
    *   In headless mode, rendering systems are skipped during the normal update loop to save resources.
    *   However, the `GameDriver` can force a render pass when a screenshot is requested.

## Usage

### 1. Setting up the Environment

Use the `test_environment` context manager to ensure your test doesn't try to open a window. This is typically done in a `conftest.py` fixture or directly in the test function.

```python
from src.yukkuri_game.testing.environment import test_environment

def test_my_feature():
    with test_environment():
        # Your test code here
        pass
```

### 2. Writing a Scenario

A scenario is a Python generator function that yields commands. The `GameDriver` iterates through this generator, executing commands and advancing the game loop.

**Available Commands:**

*   `WaitFrames(n)`: Run the game for `n` frames.
*   `WaitUntil(predicate, timeout)`: Run the game until the `predicate` function returns `True`.
*   `InjectInput(events)`: Inject a list of Pygame events.
    *   Helpers: `Click(x, y)`, `KeyPress(key)`
*   `Screenshot(filename)`: Save a screenshot to the specified path.
*   `Callable`: If you yield a simple function, it will be executed immediately.

**Example Scenario:**

```python
from src.yukkuri_game.testing.driver import WaitFrames, WaitUntil, Click, Screenshot

def my_scenario(game):
    # Wait for the game to stabilize
    yield WaitFrames(60)

    # Click on a button at (100, 100)
    yield Click(100, 100)

    # Wait until a Yukkuri appears
    yield WaitUntil(lambda: game.world.get_entity_count() > 0)

    # Take a screenshot
    yield Screenshot("screenshots/test_result.png")
```

### 3. Helper Methods

The `GameDriver` provides several typed helpers for querying state and asserting conditions without writing boilerplate loops:

*   **Component Helpers**:
    *   `driver.get_component(entity_id, ComponentType)`: Retrieves a specific component safely, returning `None` if not found.
    *   `driver.assert_component(entity_id, ComponentType, predicate)`: Asserts a component matches a condition with a clean error message.
*   **Event Helpers**:
    *   `driver.get_events(EventType)`: Returns a filtered list of all intercepted events of that type.
    *   `driver.assert_event_published(EventType, count=None)`: Asserts an event was published exactly `count` times, or at least once if omitted.
*   **Execution Helpers**:
    *   `driver.run_until(predicate, timeout=10.0)`: Bypasses the need to yield a generator; runs the game directly until the condition is met or times out.

### 4. Running the Test with `GameDriver`

Instantiate the `YukkuriGame` and `GameDriver`, then run the scenario.

```python
from src.yukkuri_game.main import YukkuriGame
from src.yukkuri_game.testing.driver import GameDriver
from src.yukkuri_game.testing.environment import test_environment

def test_game_interaction():
    with test_environment():
        # Initialize game in headless mode
        game = YukkuriGame(headless=True)
        driver = GameDriver(game)

        # Define the scenario
        def scenario():
            yield WaitFrames(10)
            # ... more steps ...

        # Run the scenario with a timeout
        driver.run_scenario(scenario(), timeout=5.0)

        # Assertions after the scenario
        assert game.some_state == expected_value
```

## Advanced Usage

### Screenshots in Headless Mode

Even though the game runs without a window, `SDL_VIDEODRIVER=dummy` allows Pygame to maintain a software surface. The `GameDriver`'s `save_screenshot` method (invoked by the `Screenshot` command) will:

1.  Initialize the `RenderSystem` (if it wasn't initialized due to headless optimization).
2.  Force a render pass to the surface.
3.  Save the surface to a file.

This is useful for visual regression testing or debugging failure states.

### Determinism

The `GameDriver` seeds the random number generators (`random` and `numpy.random`) at the start of `run_scenario`. This ensures that random events (like entity spawning or AI decisions) happen the same way every time, provided the code logic hasn't changed.

### Time Control

The `GameDriver` uses a fixed delta time (`fixed_dt`, default 1/60s) for every tick. It bypasses the real-time clock, meaning the test runs as fast as the CPU allows. `WaitFrames(60)` advances the game state by exactly 1 simulated second, regardless of how much real time it takes to compute those frames.
