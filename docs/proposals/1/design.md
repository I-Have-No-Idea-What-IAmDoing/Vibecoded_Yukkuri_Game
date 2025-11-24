# Automated Headless Testing Design (Revised)

## Problem Description
The current testing infrastructure primarily relies on unit tests and manual verification. To ensure stability, we need an automated system that can verify the full game loop, rendering pipeline, and interaction logic in a deterministic, headless environment (CI/CD).

## Proposed Solution
We will implement a **Deterministic Frame-Stepping Test Harness**. Unlike a traditional "real-time" game runner, this system will drive the game loop manually, frame by frame, with a fixed timestep. This ensures 100% reproducibility of game states given the same inputs and seed.

## Key Architecture

### 1. Inversion of Control: `Game.step()`
Instead of calling `Game.run()` which enters an infinite `while` loop, we will expose a `step(dt)` method.
*   **Production:** `run()` simply calls `step(clock.tick())` in a loop.
*   **Testing:** The test runner calls `step(FIXED_DT)` (e.g., 1/60.0) in a loop.
*   **Benefit:** The test controls time. No race conditions. No waiting for "real" seconds. Tests run as fast as the CPU allows.

### 2. Determinism & Seeding
To guarantee that screenshots and logic are identical across runs:
*   **RNG:** The test harness must initialize the random seed (Python `random`, `numpy` if used) to a fixed value at the start of each test.
*   **Time:** Only the fixed `dt` is passed to update methods. `time.time()` calls inside game logic must be mocked or replaced with an internal `game_time` accumulator.

### 3. Headless Rendering Strategy
*   **Driver:** We will use `os.environ["SDL_VIDEODRIVER"] = "dummy"` to prevent a window from opening.
*   **Surface:** We will verify that `pygame.display.set_mode` returns a valid surface even with the dummy driver.
*   **Snapshotting:** A `ScreenCapturer` utility will wrap `pygame.image.save(screen, path)`.
*   **Verification:** For visual regression, we will compare generated screenshots against "golden" images using a pixel-diff algorithm with a configurable tolerance (to handle minor rendering differences across libs).

### 4. Input Injection
Input will not be simulated by "waiting" for time. It will be injected per-frame.
*   **Event Queue:** We will mock or populate the Pygame event queue using `pygame.event.post()`.
*   **Polled Input:** If the game uses `pygame.key.get_pressed()`, we must wrap this call in an `InputProvider` interface so we can return a mock state dictionary during tests.

### 5. Test Script Format (Python, not JSON)
Scenarios should be written as Python test functions (using Pytest), not external JSON files. This allows full logic:

```python
def test_movement_logic(headless_game):
    headless_game.seed(42)

    # Simulate holding right key for 60 frames
    headless_game.input.hold_key(K_RIGHT)
    for _ in range(60):
        headless_game.step(1/60.0)

    assert headless_game.player.x > 100
    headless_game.assert_screenshot("moved_right.png")
```

## Implementation Plan
1.  **Refactor Game Loop:** Extract the inner loop body into a public `step(dt)` method.
2.  **Abstract Input:** Create an `InputManager` that wraps `pygame.event.get` and `pygame.key.get_pressed`.
3.  **Create Test Fixture:** A Pytest fixture that sets up the headless environment (dummy driver, seeded RNG).
4.  **Visual Diff Tooling:** Add a helper to compare screenshots against a baseline folder.

## Rationale
This approach prioritizes **reliability**. By controlling time and input deterministically, we eliminate flakiness, enabling a robust regression suite that runs quickly in CI environments.
