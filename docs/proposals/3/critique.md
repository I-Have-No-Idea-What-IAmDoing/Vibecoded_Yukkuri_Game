# Critique of Proposal 3 (Automated Headless Testing)

## Summary
Proposal 3 improves upon Proposal 1 by introducing the concept of an "Input Agent" and explicitly mentioning "stability testing". However, it over-engineers the runner architecture (subprocess reliance) while under-engineering the actual integration mechanics, leaving critical gaps in how the test code interacts with the game loop.

## Harsh Critique

### 1. Observability Black Hole
The proposal strongly implies running the game in a subprocess (`python -m src.yukkuri_game --headless ...`). While this ensures isolation, it makes **white-box testing** nearly impossible.
*   How do you assert that `entity.health == 50`? You can't. You can only look at logs or screenshots.
*   Debugging a failure becomes a nightmare of parsing `stdout`/`stderr` instead of getting a clean stack trace in the test runner.

### 2. Pollution of Production Code
Adding CLI flags like `--test-mode`, `--scenario`, and `--test-duration` to `main.py` is bad practice. Production code should not be littered with testing logic. A dedicated test entry point (`tests/run_headless.py`) should import the game class and configure it, rather than forcing the main executable to wear multiple hats.

### 3. The "Visual Verification" Trap
The proposal leans too heavily on "Golden Testing" (comparing screenshots).
*   **Fragility:** Rendering differences across OSs (Mac vs Linux vs Windows), font rendering libraries, and even GPU drivers will cause these tests to fail constantly.
*   **Maintenance:** Every minor UI tweak requires updating *all* reference images. This is a maintenance burden that usually leads to developers disabling the tests.

### 4. "Agent" Vagueness
The "Input Agent" is described as an abstraction, but the implementation detail—"injecting events"—glosses over the synchronization problem. If the test script runs in parallel (or worse, in the same thread but without clear yield points), when does the agent "think"?
*   If it's a subprocess, how does the Agent (running in the test process) talk to the Game (running in the subprocess)? The proposal suggests the Agent runs *inside* the game via the `--scenario` script, which contradicts the external "Runner" narrative.

### Verdict
Proposal 3 has better structure but falls into the trap of treating the game as a completely black box. This limits the depth of testing to mere smoke testing and UI verification, ignoring the power of accessing internal state for robust logic verification.
