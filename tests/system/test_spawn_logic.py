"""
System test for spawning logic.
"""
import pytest
from yukkuri_game.engine.application import Application as YukkuriGame
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
    # Application doesn't have gm or world directly.
    # But GameDriver exposes world property from the current scene.
    assert game_driver.world is not None
    # Check for a core service instead of gm
    from yukkuri_game.game.services import TimeService
    assert game_driver.world.services.try_get(TimeService) is not None

def test_spawn_reimu(game_driver):
    """
    Verifies that we can spawn a Yukkuri.
    """

    def scenario():
        yield WaitFrames(5)
        # Direct state modification for setup
        # Use game_driver helper or access factory via world
        game_driver.create_yukkuri("reimu", 100, 100)
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
    # Use game_driver.world
    components = game_driver.world.get_components(YukkuriStats)

    # We expect 2 because GameplayScene creates an initial Reimu in on_enter/setup
    # and we spawned another one.
    # Wait, GameplayScene creates initial population?
    # Yes:
    # if not self.application.headless:
    #     ... self.factory.create_yukkuri("reimu", start_x, start_y)
    #
    # But we are running in headless mode. So initial population might NOT be created.
    # "if not self.application.headless:" -> correct.
    # So we expect 1 (the one we created).

    assert len(components) == 1
