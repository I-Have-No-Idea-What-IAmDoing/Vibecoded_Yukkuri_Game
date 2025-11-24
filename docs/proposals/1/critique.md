# Critique of Proposal 1 (Automated Headless Testing)

## Summary
Proposal 1 suggests a rudimentary approach to headless testing by "refactoring" the `GameLoop` and injecting inputs via a simple dictionary-based timeline. While it identifies the core need (headless rendering via `SDL_VIDEODRIVER`), the execution details are amateurish and prone to creating technical debt.

## Harsh Critique

### 1. Architectural Laziness
The proposal suggests "refactoring `YukkuriGame`" to handle offscreen surfaces. This is a classic violation of the Open/Closed Principle. The game loop should not care if it's running in a test; the *context* (window vs. dummy) should be injected or handled by a platform abstraction layer. "Just not call `pygame.display.set_mode`" is dangerous advice that demonstrates a lack of understanding of Pygame internals—many functions rely on the display surface being initialized.

### 2. Flaky Input Mechanism
The `InputScenario` structure (a list of dictionaries with timestamps) is inherently brittle.
*   **Race Conditions:** Relying on `time.time()` (or accumulated `dt`) to trigger events in a real-time loop is non-deterministic. If the frame rate hiccups, an event might fire late or be skipped if the logic isn't perfect.
*   **Rigidity:** A static list cannot react to game state (e.g., "Wait for entity X to spawn, THEN click"). This makes it useless for anything beyond trivial smoke tests.

### 3. Missing Determinism
There is **zero mention** of fixed time-steps or random seed control. Without these, tests will be flaky. Physics simulations (if any) and AI behavior will diverge across runs, making "visual verification" useless because the pixels will never match exactly.

### 4. Weak Verification
"Verify screenshot exists" is not a test; it's a placeholder. The proposal waves hands at "integration with Pytest" without explaining how a typically infinite `while True:` loop cooperates with a test runner. If the game loop blocks, the test runner cannot assert anything until the game exits.

### Verdict
This proposal is a prototype sketch, not a production-ready design. It ignores the hardest parts of game testing: determinism, synchronization, and state verification.
