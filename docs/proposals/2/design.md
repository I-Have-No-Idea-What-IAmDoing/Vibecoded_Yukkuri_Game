# Automated Headless Testing Design

## Problem Statement
Testing game interactions manually is time-consuming and prone to human error. Visual regressions or logic bugs can be missed during manual playtesting. To ensure the stability of the *Yukkuri Raising Game*, we need a system that can automatically run the game, simulate user inputs, and verify the visual output, all without requiring a physical display (headless mode). This enables Continuous Integration (CI) pipelines to run these tests.

## Rationale
- **Regression Testing:** Ensures that new changes do not break existing game mechanics.
- **Visual Verification:** Screenshots allow for visual regression testing (comparing against gold standard images).
- **Performance:** Headless testing is generally faster and can be parallelized.
- **Automation:** Allows for "nightly builds" or pre-merge checks.

## Design

### 1. Headless Environment
The system will leverage `pygame-ce`'s ability to use a dummy video driver. This allows the game to run "normally" but without opening a window on the host machine.

```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
```

This must be set before `pygame.init()` is called.

### 2. Test Runner Architecture
We will introduce a `TestRunner` or `HeadlessGame` wrapper around the main `YukkuriGame` class. This runner will:
- Initialize the game in headless mode.
- Load a "Scenario" or "Input Script".
- Execute the game loop for a deterministic number of frames or time duration.
- Inject input events at specific timestamps.
- Trigger screenshots at specific timestamps.
- Assert conditions (e.g., entity count, specific game state variables).

### 3. Input Simulation
To simulate human-like control, we need to inject events into the Pygame event queue or directly into the `InputSystem`.

**Approach A: Event Injection (Preferred)**
We can construct `pygame.event.Event` objects and push them to the queue using `pygame.event.post()`. This ensures the game processes inputs exactly as if they came from the OS.

```python
# Example: Simulate a mouse click at (100, 200) at frame 60
if current_frame == 60:
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (100, 200)})
    pygame.event.post(event)
```

**Approach B: Direct Service Calls**
Calling `input_service.start_placement(...)` directly. This is easier for unit tests but less "integration-like" than Event Injection. For this proposal, we prioritize **Event Injection** to test the full stack.

### 4. Scenario Definition
Scenarios can be defined in JSON or Python scripts.
Example JSON structure:
```json
{
  "duration_seconds": 10,
  "events": [
    {"time": 1.0, "type": "MOUSEBUTTONDOWN", "button": 1, "pos": [400, 300]},
    {"time": 1.1, "type": "MOUSEBUTTONUP", "button": 1, "pos": [400, 300]},
    {"time": 5.0, "type": "SCREENSHOT", "name": "mid_game_check"}
  ]
}
```

### 5. Visual Verification (Screenshots)
The game already has a `take_screenshot` method. The `TestRunner` will trigger this method based on the scenario. The resulting images can be saved to an artifacts directory for manual review or automated comparison.

### 6. Automatic Stopping
The `TestRunner` will monitor the elapsed time or frame count. Once the limit is reached, it will signal the game to exit (e.g., setting `game.running = False`).

## Implementation Details

### Directory Structure
- `tests/headless/`: Directory for headless test scripts and scenarios.
- `tests/headless/scenarios/`: JSON files defining test scenarios.
- `tests/headless/screenshots/`: Output directory for test artifacts.

### Modifications to `YukkuriGame`
- Ensure `YukkuriGame` can accept an external clock or update loop control if strictly deterministic timing is needed (optional but recommended for flaky tests).
- Ensure `pygame.quit()` is called cleanly at the end of a test to prevent hanging processes.

## Comparison with Existing Systems
- **PyTest-Pygame:** Some libraries exist but often lack robust event injection for complex GUIs like `pygame-gui`.
- **Selenium/Playwright:** Great for web, but not applicable to native Pygame (unless we compile to WebAssembly).
- **Custom Scripting:** Most game studios build custom harnesses. Our approach mimics this by wrapping the game loop.

## Future Work
- **Visual Diffing:** Automatically compare generated screenshots with "golden" images using `opencv` or `PIL`.
- **Randomized "Fuzz" Testing:** sending random inputs to try and crash the game.
