# Automated Deterministic Headless Testing System

## Abstract
This proposal defines a robust architecture for automated system testing of the Yukkuri Game. It synthesizes the strengths of previous proposals (Headless rendering, Scenarios) while addressing their critical flaws (Determinism, Observability, Code Pollution). The core innovation is a **Generator-based Test Controller** that runs *inside* the game loop, allowing synchronous, deterministic interaction with the game state without threading race conditions or black-box limitations.

## Core Philosophy
1.  **Determinism is King:** Tests must be 100% reproducible. This requires a fixed time-step loop and explicit RNG seeding.
2.  **White-Box Access:** The test runner must have direct access to the `YukkuriGame` instance to assert internal state (e.g., `assert yukkuri.hunger < 50`), not just look at pixels.
3.  **Separation of Concerns:** Production code (`main.py`) stays clean. We introduce a dedicated `TestLauncher` that constructs the game in a test configuration.

## Design

### 1. The `HeadlessGame` Subclass
Instead of modifying `YukkuriGame` with `if self.is_headless:`, we create a subclass (or a composition wrapper) specifically for testing.

```python
# src/yukkuri_game/testing/headless_game.py

class HeadlessGame(YukkuriGame):
    def __init__(self, scenario, seed=42):
        # Force dummy driver
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        super().__init__()

        # Deterministic Seeding
        random.seed(seed)
        np.random.seed(seed)

        # Inject the scenario
        self.scenario_generator = scenario(self)

    def run(self):
        # Override the main loop to control time
        while self.running:
            # Fixed Time Step (e.g., 1/60s)
            dt = 1.0 / 60.0

            # 1. Process System Events (Quit, etc.)
            self.process_events()

            # 2. Step the Scenario (Inject Inputs / Assertions)
            try:
                next(self.scenario_generator)
            except StopIteration:
                self.running = False # End of test
            except Exception as e:
                self.fail(e)

            # 3. Update Game Logic
            self.update(dt)

            # 4. Render (to offscreen surface)
            self.draw()
```

### 2. Scenario as a Coroutine
Scenarios are Python generators. This allows natural, readable logic that "yields" control back to the game loop for one frame.

```python
def simple_spawn_scenario(game):
    # Wait for initialization
    for _ in range(60): yield # Wait 1 second (60 frames)

    # Inject Input
    game.input_system.inject_click(x=100, y=100)

    # Wait for reaction
    for _ in range(30): yield

    # White-box Assertion
    assert len(game.entity_manager.entities) == 1

    # Screenshot for debug/goldens
    game.save_screenshot("spawn_test.png")
```

### 3. The Test Runner
A simple script or Pytest fixture that:
1.  Instantiates `HeadlessGame` with a specific `scenario`.
2.  Runs it.
3.  Catches exceptions propagated from the scenario.

### 4. Input Injection
Instead of posting low-level Pygame events (which are asynchronous and can be erratic), the `HeadlessGame` will expose a direct `InputProxy` that modifies the input state directly or posts events synchronously at the start of the frame.

### 5. Verification Strategy
*   **State Verification (Primary):** `assert game.state.x == y`. Robust and strictly logic-based.
*   **Visual Verification (Secondary):** Save screenshots on failure or at specific checkpoints. Use a "perceptual hash" or simple file existence check rather than strict pixel comparison to reduce flakiness.

## Comparison to Previous Proposals
*   **vs Prop 1:** Uses a generator/coroutine model instead of a rigid list of dicts. This allows logic (`if x: do y`) in tests.
*   **vs Prop 3:** Runs in-process (white-box) instead of subprocess (black-box). Solves the observability problem. Uses inheritance to keep `main.py` clean. Enforces fixed time-steps for determinism.

## Implementation Tasks
See `tasks.md`.
