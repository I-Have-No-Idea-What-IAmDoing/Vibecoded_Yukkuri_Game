# Critique of Proposal 1 (Automated Headless Testing)

## Summary
Proposal 1 identifies the correct problem (lack of automated integration testing) but proposes a solution that is fragile, under-specified, and likely to introduce flakiness. The suggested approach for input simulation and verification is naive and lacks the rigor required for a reliable CI/CD pipeline.

## Harsh Critique

### 1. Architectural Smells & Implementation Vagueness
The proposal wavers between `SDL_VIDEODRIVER="dummy"` and "offscreen `pygame.Surface`" without committing. These are fundamentally different approaches with different trade-offs (e.g., `dummy` driver might not allow software rendering to work as expected for screenshots depending on the platform). "Just not calling `pygame.display.set_mode`" is a recipe for crashes in Pygame, which often expects a display surface for image loading and conversion operations. Modifying `YukkuriGame` directly to support this is invasive; a better design would use dependency injection for the renderer or display context.

### 2. The Input Simulation is Naive
The proposed `InputScenario` using a list of dictionaries with timestamps (`"time": 1.0`) is deeply flawed.
*   **Nondeterminism:** Frame times vary. Triggering an event at exactly `t=1.0` is impossible; it will happen at `t=1.0 + delta`. If game logic depends on frame alignment, this will flake.
*   **Blind Execution:** The script fires events blindly without checking if the game is ready (e.g., clicking a button that hasn't loaded yet).
*   **Mechanism:** Using `pygame.fastevent.post` assumes the game relies solely on the event queue. If the code polls `pygame.key.get_pressed()`, these injected events will be ignored. The proposal does not verify how input is actually consumed.

### 3. Zero Focus on Determinism
**This is the biggest failure.** A testing system without determinism is useless. The proposal does not mention:
*   **Fixed Timestep:** Without a fixed `dt`, physics and animations will drift.
*   **RNG Seeding:** Random events will break replayability.
*   **Asset Loading:** Ensuring all assets are loaded before the "timer" starts.
Without these, screenshot comparison is impossible because pixel-perfect matches will never happen.

### 4. "Visual Verification" is a Pipe Dream here
"Asserts that screenshots match expected baselines" is thrown in as an "optional" afterthought. Visual regression is incredibly hard to get right (anti-aliasing differences across OS, font rendering differences). Without a strict plan for handling fuzzy matching or environment normalization (e.g., running in a Docker container), this feature will result in constant false positives.

### 5. Process Model Confusion
How does `HeadlessTestRunner` interact with Pytest? Pygame's loop is blocking. Does the runner run in a thread? Subprocess? Or does it invert control (yield control back to the test runner per frame)? The proposal says "hooks into the update loop," which is messy. A "Frame-by-Frame" stepping approach driven by the test (synchronous execution) is far superior to a "Real-time" runner for testing.

### Verdict
**Reject and Revise.** The proposal needs to pivot from "running the game in real-time with a script" to "stepping the game deterministically frame-by-frame." It must address RNG seeding, input polling vs. events, and platform-independent rendering.
