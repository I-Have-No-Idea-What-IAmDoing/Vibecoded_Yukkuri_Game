# Critique of Proposal 3 (Automated Headless Testing)

## Summary
Proposal 3 presents a more structured approach than Proposal 1 but suffers from "Black Box Syndrome." It advocates for running the game as a separate process via CLI flags, which severely limits the ability to verify internal state and debug failures. It also relies heavily on fragile visual regression testing without addressing the cross-platform maintenance nightmare.

## Harsh Critique

### 1. The "Subprocess" Anti-Pattern
The proposal suggests running the game via `python -m src.yukkuri_game --scenario ...`. This effectively treats the game as a black box.
*   **No State Inspection:** You cannot assert `game.player.health == 100` because the game memory is in a different process. You are limited to parsing logs or analyzing screenshots.
*   **Debugging Hell:** If the game crashes or hangs, you get an exit code, not a stack trace integrated with your test runner (Pytest).
*   **IPC Overhead:** If you want to control the game dynamically (e.g., "Wait for X to spawn"), you need complex Inter-Process Communication (IPC) or a pre-defined script that can't react to game state.

### 2. Polluting Production Code
Adding flags like `--test-mode`, `--scenario`, and `--duration` to the main game executable is sloppy.
*   **Bloat:** Production binaries shouldn't carry test harness logic.
*   **Security:** Exposing debug/test paths in the main executable can lead to exploits or accidental activation in production.
*   **Separation of Concerns:** A `TestRunner` should *import* the game logic, not *flag* the game executable to behave differently.

### 3. Visual Verification Naivety
"Screenshots allow verifying rendering... comparison against reference images."
*   **Cross-Platform Nightmare:** Font rendering and anti-aliasing differ between Linux, Windows, and macOS. Golden images generated on a dev machine will fail in CI (Linux).
*   **Maintenance Burden:** A 1-pixel shift in a UI element invalidates *every* screenshot. This leads to "snapshot fatigue" where devs just blindly update snapshots without checking.
*   **Solution Missing:** The proposal lacks any mention of fuzzy matching, perceptual hashing, or tolerance thresholds.

### 4. Input "Injection" vs. "Simulation"
The proposal mentions "injecting `pygame.event.Event`". This is good, but it misses the timing aspect.
*   **Frame Synchronization:** If the "Agent" posts 10 events, do they happen in 1 frame or 10? The proposal doesn't define the temporal relationship between the script and the game loop.
*   **Blocking:** If the scenario script says `agent.wait(5)`, does it block the game loop? Or does it yield? The concurrency model is undefined.

### Verdict
**Reject and Revise.** Move away from the CLI/Subprocess model. Embrace an "Embedded" model where the test runner *is* the main entry point and the game is an object controlled by the test. Replace strict screenshot matching with structural verification (state inspection) and fuzzy visual checks.
