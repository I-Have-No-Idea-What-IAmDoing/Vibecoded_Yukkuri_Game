# Automated Headless Testing System (Revised)

## Abstract
This proposal outlines a **White-Box, In-Process Headless Testing System**. Instead of treating the game as a black box executable, we will instantiate the `YukkuriGame` class directly within a Pytest environment. This allows for direct state inspection, deterministic frame control, and robust regression testing without polluting the production entry point.

## Rationale
Testing a game effectively requires more than just checking if it runs. We need to verify that game logic (physics, AI, stats) behaves correctly over time.
*   **White-Box vs. Black-Box:** By running in-process, tests can assert `player.health == 0` directly, rather than inferring it from a "Game Over" screen.
*   **Determinism:** Controlling the clock allows us to skip "waiting" in real-time. A 10-minute game scenario can run in seconds.
*   **Stability:** Direct exception handling allows the test runner to catch and report crashes with full context.

## Design

### 1. In-Process Test Architecture
We will not add flags to `main.py`. Instead, we will create a `TestGame` wrapper class that inherits from or wraps `YukkuriGame`.
*   **`TestGame`**: Overrides the `run()` loop to expose a `tick()` or `step()` method.
*   **Pytest Integration**: A `game_instance` fixture will provide a fresh, headless `TestGame` for each test.

### 2. Headless Configuration
The `game_instance` fixture will handle the environment:
```python
@pytest.fixture
def game_instance():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    game = YukkuriGame(config={"window": {"width": 800, "height": 600}})
    game.initialize() # Setup without starting the loop
    return game
```

### 3. The "Director" (Input & Time Control)
A `Director` helper object will manage the flow of the test.
*   **`director.step(frames=1)`**: Advances the game logic by a fixed `dt` (e.g., 1/60s) per frame.
*   **`director.fast_forward(seconds)`**: Loops `step` for the calculated number of frames.
*   **`director.input.click(pos)`**: Queues a mouse event for the *next* step.
*   **`director.input.press(key)`**: Sets the mocked key state for the *duration* of subsequent steps until released.

### 4. Verification Strategy

#### A. State Verification (Primary)
Tests should primarily verify internal state.
```python
def test_yukkuri_starvation(game, director):
    yukkuri = game.spawn_yukkuri()
    director.fast_forward(seconds=300) # Fast forward 5 minutes
    assert yukkuri.hunger < 50
    assert yukkuri.state == "hungry"
```

#### B. Visual Verification (Secondary)
Screenshots are useful for catching rendering crashes or gross artifacts.
*   **Snapshot Testing**: Use `pytest-snapshot` or similar to manage golden images.
*   **Fuzzy Matching**: Comparison must allow for a small % of pixel difference (thresholding) to handle cross-platform rendering nuances.
*   **Artifacts**: Screenshots from failing tests are automatically attached to the test report.

### 5. Determinism Enforcement
*   **Mocking Time:** `time.time()` and `pygame.time.get_ticks()` inside the game must be patchable or derived from the `Director`'s internal clock.
*   **Seeding:** The fixture will automatically seed `random` and `numpy.random` with a constant (or a value derived from the test name) to ensure replayability.

## Workflow
1.  **Write Test:** Create a `.py` file in `tests/integration/`.
2.  **Run:** `pytest tests/integration/`.
3.  **Debug:** If a test fails, Pytest provides the diff of the assertion (e.g., `assert 49 < 50` failed) and the stack trace.

## Implementation Tasks
1.  **Refactor `YukkuriGame`**: Ensure `initialize()` is separate from `run()`. Allow dependency injection for the "Clock" and "Input" systems.
2.  **Create `TestGame` Wrapper**: Implement the `step()` logic.
3.  **Implement `Director`**: Build the helper for advancing time and injecting events.
4.  **CI Setup**: Configure GitHub Actions (or equivalent) to install `libsdl2-dev` (if needed for dummy driver) and run the suite.
