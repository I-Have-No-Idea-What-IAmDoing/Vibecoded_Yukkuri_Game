# Automated Deterministic Headless Testing System (Revised)

## Abstract
This proposal defines a robust architecture for automated system testing of the Yukkuri Game. It focuses on **Determinism**, **Observability**, and **Separation of Concerns**. The core innovation is a **Composition-based Test Controller** that drives the standard game loop synchronously, injecting inputs via standard event queues and verifying state via direct object inspection.

## Core Philosophy
1.  **Determinism is King:** Tests must be 100% reproducible. This requires a fixed time-step loop, explicit RNG seeding, and isolation from wall-clock time.
2.  **Test the Real Thing:** We test the actual `YukkuriGame` class, not a "test subclass". We avoid mocking core logic.
3.  **Robust Synchronization:** We wait for *conditions* (predicates), not *time* (frames).
4.  **Clean Environments:** Global state (env vars) is managed safely and isolated.

## Design

### 1. The `GameDriver` (Composition over Inheritance)
Instead of subclassing `YukkuriGame`, we create a `GameDriver` class that *owns* and *controls* an instance of `YukkuriGame`.

*   **Responsibility:** The `GameDriver` is responsible for setting up the environment (SDL drivers), initializing the game with a deterministic seed, and manually ticking the game loop.
*   **Mechanism:** It acts as a wrapper. It does not replace `main.py`, but mimics `main.py`'s loop structure in a controlled way.

```python
# Conceptual Usage
with TestEnvironment() as env:
    game = YukkuriGame(config=env.config)
    driver = GameDriver(game)
    driver.run_scenario(my_test_scenario)
```

### 2. Scenario as a Generator with Predicates
Scenarios are Python generators that yield *commands* or *wait conditions* back to the driver. This avoids brittle "sleep for X frames" logic.

*   **Wait for Condition:** `yield WaitUntil(lambda: game.entities.count > 0)`
*   **Wait for Time:** `yield WaitFrames(60)` (Use sparingly, for animations only)
*   **Action:** `yield InjectInput(Click(100, 100))`

The driver iterates the generator. If it yields a `WaitUntil`, the driver ticks the game loop until the predicate is true or a timeout is reached.

### 3. Input Injection via Event Queue
To ensure we test the full input pipeline, we do NOT mutate input state directly.
*   **Mechanism:** We inject synthetic `pygame.event` objects into the queue using `pygame.event.post()` (or by mocking the event getter if strictly necessary, but `post` is preferred for realism).
*   **Advantage:** This tests the game's event handling logic (e.g., did we click on a UI element or the map?).

### 4. Deterministic Loop & Time
The `GameDriver` runs the loop manually.
*   It passes a fixed `dt` (e.g., 1/60.0) to `game.update(dt)`.
*   It ensures `time.time()` calls (if any) are mocked or that the game uses a passed-in time accumulator.
*   **RNG:** The driver explicitly seeds `random` and `numpy.random` before game initialization.

### 5. Environment & CI/CD
*   **Headless Video:** We use the `SDL_VIDEODRIVER=dummy` environment variable. This is set using a `contextmanager` to ensure it is unset after the test, preventing pollution of other tests.
*   **Headless Audio:** We set `SDL_AUDIODRIVER=dummy` or `disk` to prevent failures on CI servers lacking audio hardware.
*   **Timeout:** The `GameDriver` enforces a strict timeout (e.g., 10 seconds of simulated time) to prevent infinite loops in broken tests.

### 6. Verification Strategy
*   **State Verification (Primary):** `assert game.state.x == y`.
*   **Visual Verification (Optional):**
    *   **Snapshots:** The driver can trigger `game.render()` to a surface and save it.
    *   **Golden Management:** We will use a dedicated library (like `pytest-regressions` or custom) to manage baseline images.
    *   **Failure Only:** By default, screenshots are only saved/checked if a state assertion fails, or explicitly requested in the scenario.

## Implementation Plan

1.  **Refactor Game Loop:** Ensure `YukkuriGame` has a `tick(dt)` method that separates logic from the `while True` loop, making it drivable.
2.  **Create `TestEnvironment` Context Manager:** Handles SDL env vars.
3.  **Implement `GameDriver`:** The core runner that handles the generator and ticks the game.
4.  **Implement Wait Predicates:** `WaitUntil`, `WaitFrames`.
5.  **Implement Input Helpers:** `Click`, `KeyPress` wrappers around `pygame.event.post`.

See `tasks.md` for the breakdown.
