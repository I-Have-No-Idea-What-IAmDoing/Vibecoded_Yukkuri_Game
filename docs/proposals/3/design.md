# Automated Headless Testing System

## Abstract

This proposal outlines the design for an **Automated Headless Testing** system for the Yukkuri Game. The system aims to enable continuous integration (CI) testing, regression verification, and long-running stability checks by running the game without a graphical window (headless). It introduces mechanisms to simulate user inputs, control game execution time, and capture visual states via screenshots for verification.

## Rationale

Currently, the project relies on unit and integration tests that often mock the rendering subsystem (Pygame) and input handling. While these tests are fast and effective for checking logic, they have limitations:
1.  **Rendering Regressions**: Mocking `pygame` hides bugs related to surface handling, drawing order, or resource loading.
2.  **Integration Gaps**: Mocks may not perfectly replicate the behavior of the real game loop or event queue.
3.  **Manual Testing Dependency**: Verifying the game "looks right" or "plays right" for longer sessions currently requires a human tester.

A headless testing system addresses these issues by:
*   **Running the Real Game Loop**: Using `SDL_VIDEODRIVER=dummy` allows the actual Pygame loop to run on CI servers.
*   **Automated "Gameplay"**: By injecting inputs or using high-level agents, we can simulate user behavior (placing items, moving camera) automatically.
*   **Visual Verification**: Screenshots taken during the test can be compared against reference images (Golden Testing) or reviewed manually to ensure no graphical corruption occurs.
*   **Stability Testing**: Long-running headless tests can catch memory leaks or rare race conditions that unit tests miss.

## Design

### 1. Headless Environment
The system will utilize Pygame's support for the dummy video driver.
*   **Environment Variable**: `os.environ["SDL_VIDEODRIVER"] = "dummy"` must be set *before* `pygame.init()` is called.
*   **Resolution**: The game should be initialized with a standard testing resolution (e.g., 1280x720) to ensuring consistent screenshot comparison.

### 2. Test Runner
A dedicated `TestRunner` or a modification to the main entry point (`main.py` / `YukkuriGame`) is required.
*   **Command Line Interface**: New flags will be added:
    *   `--headless`: Enables the dummy driver.
    *   `--test-mode`: Activates the testing harness (disables VSync, may run at fixed time-step).
    *   `--duration <seconds>`: Automatically quits the game after X seconds.
    *   `--scenario <path>`: Loads a specific test scenario (see below).

### 3. Input Simulation (The "Ghost User")
To test the game "controlled in a similar fashion as a human", we need an input injection layer.
*   **Input Agent**: An abstraction that can queue actions.
    *   `agent.click(x, y, button)`
    *   `agent.type(text)`
    *   `agent.wait(seconds)`
*   **Implementation**: The agent will inject `pygame.event.Event` objects into the Pygame event queue (`pygame.event.post`) or directly interact with the `InputSystem` services if lower-level control is needed. However, injecting events is preferred as it tests the entire pipeline including event handling logic.

### 4. Scenarios
Tests will be defined as "Scenarios".
*   **Structure**: A Python script or a configuration file (YAML/TOML) defining:
    1.  **Setup**: Initial world state (load a specific map, spawn entities).
    2.  **Action Timeline**: A list of actions the Input Agent should perform at specific timestamps.
    3.  **Checkpoints**: Times to take screenshots or assert specific game states (e.g., "Entity count should be > 5").

### 5. Visual Verification (Screenshots)
*   **Mechanism**: `pygame.image.save(screen_surface, filename)`.
*   **Timing**:
    *   Scheduled: "Take screenshot at t=5s, t=10s".
    *   On Event: "Take screenshot after placing item".
    *   On Exit: Always capture final state.
*   **Output**: Saved to `tests/results/<timestamp>/` or similar.

### 6. Determinism (Synthesized Improvement)
To make tests reproducible (synthesized from best practices):
*   **Seed Control**: Allow setting random seeds for `random`, `numpy`, and `python` hashing.
*   **Fixed Time Step**: Instead of relying on wall-clock `dt`, the test runner should force a fixed delta time (e.g., 1/60th sec) per frame to ensure physics and logic behave identically across runs.

## Workflow

1.  **Developer** writes a scenario (e.g., "Spawn 10 Yukkuris and wait 30 seconds").
2.  **CI System** runs `python -m src.yukkuri_game --headless --scenario tests/scenarios/spawn_test.py`.
3.  **Runner** executes the game, injects inputs, takes screenshots.
4.  **Runner** exits with status 0 if successful (no crashes, assertions passed), 1 otherwise.
5.  **Artifacts** (screenshots, logs) are saved for review.
