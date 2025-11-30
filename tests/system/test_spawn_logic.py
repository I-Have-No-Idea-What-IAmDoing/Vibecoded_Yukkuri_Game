"""
System test for spawning logic.
"""
import pytest
from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import WaitUntil, WaitFrames, Click, Screenshot

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
    from yukkuri_game.game.game_manager import GameManager
    from yukkuri_game.game.yukkurrium import Yukkurrium
    assert game_driver.world.services.try_get(GameManager) is not None
    assert game_driver.world.services.try_get(Yukkurrium) is not None

def test_spawn_reimu(game_driver):
    """
    Verifies that we can spawn a Yukkuri.
    """

    def scenario():
        yield WaitFrames(5)
        # Direct state modification for setup
        from yukkuri_game.game.entity_factory import EntityFactory
        factory = game_driver.world.services.try_get(EntityFactory)
        factory.create_yukkuri("reimu", 100, 100)
        yield WaitFrames(5)

        # Test input injection alias (won't do anything without UI logic hooked up to clicks)
        yield Click(200, 200)
        yield WaitFrames(1)

        # Take a screenshot
        yield Screenshot("screenshots/test_spawn_reimu.png")

    game_driver.seed_rng(42)
    game_driver.run_scenario(scenario())

    # Verify entity count
    from yukkuri_game.game.yukkuri_components import YukkuriStats

    # game.world.get_components return dict{entity_id: component}
    components = game_driver.world.get_components(YukkuriStats)
    # We expect at least one Reimu
    assert len(components) >= 1
