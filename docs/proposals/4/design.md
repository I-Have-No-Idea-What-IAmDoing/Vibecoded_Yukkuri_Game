# Automated Deterministic Headless Testing System (Revised)

## Abstract
This proposal defines a **Composition-Based, External-Drive Headless Testing Architecture**. Unlike previous proposals that try to embed the test runner inside the game loop, this design places the Test Runner strictly *outside* the game. The Game is treated as a "steppable" state machine. The test runner owns the loop, advances time, and asserts state. This maximizes compatibility with Pytest and ensures that test logic remains standard, linear Python code.

## Core Philosophy
1.  **Inversion of Control:** The Game does not `run()`. The Test Runner `steps()` the game.
2.  **Dependency Injection:** The Game accepts `InputSource` and `TimeSource` interfaces, allowing tests to inject mocks without subclassing hacks.
3.  **Strict Determinism:** Physics and Logic run on a fixed accumulator (e.g., 60Hz). Rendering is decoupled and only happens when requested by the test (or every frame if checking for crashes).

## Design

### 1. Refactoring for Injection
We must modify `YukkuriGame` to accept its dependencies.

```python
class YukkuriGame:
    def __init__(self, config, input_manager=None, clock=None, renderer=None):
        self.input = input_manager or RealPygameInput()
        self.clock = clock or RealPygameClock()
        self.renderer = renderer or RealPygameRenderer()

    def step(self, dt):
        # The core logic, detached from the "while True" loop
        self.input.process()
        self.update(dt)
        self.renderer.draw()
```

### 2. The Test Fixture (Composition)
The test runner creates the game instance and holds a reference to the mocked inputs.

```python
# tests/conftest.py
@pytest.fixture
def headless_game():
    # 1. Setup Mocks
    mock_input = MockInput()
    mock_clock = MockClock() # Always returns fixed dt

    # 2. Configure Headless Environment
    os.environ["SDL_VIDEODRIVER"] = "dummy"

    # 3. Instantiate
    game = YukkuriGame(
        config=test_config,
        input_manager=mock_input,
        clock=mock_clock
    )
    game.initialize()
    return GameController(game, mock_input)
```

### 3. The `GameController` Helper
A helper class allows tests to write expressive, synchronous logic.

```python
class GameController:
    def __init__(self, game, input_mock):
        self.game = game
        self.input = input_mock

    def wait(self, frames=1):
        for _ in range(frames):
            self.game.step(dt=1.0/60.0)

    def wait_seconds(self, seconds):
        self.wait(frames=int(seconds * 60))

    def click(self, x, y):
        self.input.queue_click(x, y)
        self.wait(1) # Process the click
```

### 4. Test Example (Standard Python)
No generators. No custom loops. Just linear execution.

```python
def test_spawn_logic(headless_game):
    # Setup
    headless_game.game.world.load("test_map")

    # Action
    headless_game.click(200, 200) # Spawn at 200,200
    headless_game.wait_seconds(2.0)

    # White-box Assertion
    assert len(headless_game.game.entities) == 1
    entity = headless_game.game.entities[0]
    assert entity.pos == (200, 200)

    # Optional Visual Check
    headless_game.assert_screenshot("spawn_result.png")
```

### 5. Input Handling Strategy
To ensure the test input is actually used:
*   **Events:** `MockInput` will populate a list that `pygame.event.get` would usually return. The `YukkuriGame` must call `self.input.get_events()` instead of `pygame.event.get()`.
*   **Polling:** `MockInput` will maintain a dictionary of key states. `YukkuriGame` must call `self.input.is_pressed(K_SPACE)` instead of `pygame.key.get_pressed()[K_SPACE]`.

## Implementation Tasks
1.  **Interface Extraction:** Create `InputManager` and `RenderManager` interfaces in the production code.
2.  **Dependency Injection:** Update `YukkuriGame.__init__` to accept these interfaces.
3.  **Mock Implementation:** Create `MockInput` and `HeadlessRenderer` in the test suite.
4.  **Test Migration:** Port existing logic to use the new `GameController` pattern.

## Rationale
This design prioritizes **maintainability**. Tests look like standard Python code. The production code becomes cleaner (decoupled from SDL via interfaces). Determinism is enforced by the architecture, not by the OS.
