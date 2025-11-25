"""
System test for spawning logic.
"""
import pytest
from yukkuri_game.main import YukkuriGame
from yukkuri_game.testing.predicates import WaitUntil, WaitFrames
from yukkuri_game.testing.input_helpers import post_mouse_click, post_click, Click

# Note: game_driver fixture is now in conftest.py

def test_initial_setup(game_driver):
    """
    Verifies that the game initializes correctly.
    """
    def scenario():
        # Wait for game to initialize (e.g. 2 frames)
        yield WaitFrames(2)

    game_driver.run_scenario(scenario())

    assert game_driver.game.headless is True
    assert game_driver.game.gm is not None
    assert game_driver.game.world is not None

def test_spawn_reimu(game_driver):
    """
    Verifies that we can spawn a Yukkuri.
    """

    def scenario():
        yield WaitFrames(5)
        # We can inject input or call methods directly?
        # Let's try to spawn one using factory directly to verify we can control state
        # The proposal encouraged "Action: yield InjectInput(Click(100, 100))"
        # But for direct test logic, we can also modify state.
        # But let's stick to blackbox if possible?
        # Spawning usually happens via UI interaction in real game (click "Place" then click "Map").
        # If UI is not set up in default start, we might need to rely on direct calls for this specific test
        # UNLESS we set up the UI state.

        # For this test, let's keep the direct factory call to prove the driver works with mix of code.
        game_driver.game.factory.create_yukkuri("reimu", 100, 100)
        yield WaitFrames(5)

        # Test input injection alias (won't do anything without UI logic hooked up to clicks)
        yield Click(200, 200)
        yield WaitFrames(1)

    game_driver.seed_rng(42)
    game_driver.run_scenario(scenario())

    # Verify entity count
    from yukkuri_game.game.yukkuri_components import YukkuriStats

    # game.world.get_components return dict{entity_id: component}
    components = game_driver.game.world.get_components(YukkuriStats)
    assert len(components) == 1

    # Take a screenshot manually to verify success screenshot
    game_driver.save_screenshot("screenshots/test_spawn_reimu.png")
