"""
System test for spawning logic.
"""
import pytest
from yukkuri_game.main import YukkuriGame
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.testing.environment import TestEnvironment
from yukkuri_game.testing.predicates import WaitUntil, WaitFrames
from yukkuri_game.testing.input_helpers import post_mouse_click

@pytest.fixture
def game_driver():
    with TestEnvironment():
        game = YukkuriGame()
        driver = GameDriver(game)
        yield driver
        # Teardown if needed

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
    (Although currently main.py spawns a reimu by default in non-headless mode,
     but in headless mode it might not? Let's check main.py)
    """
    # In main.py setup:
    # if not self.headless:
    #     self.factory.create_yukkuri("reimu", start_x, start_y)

    # So in headless, we start with 0 entities?

    def scenario():
        yield WaitFrames(5)
        # We can inject input or call methods directly?
        # Let's try to spawn one using factory directly to verify we can control state
        game_driver.game.factory.create_yukkuri("reimu", 100, 100)
        yield WaitFrames(5)

    game_driver.seed_rng(42)
    game_driver.run_scenario(scenario())

    # Verify entity count
    # How to query entities?
    # game_driver.game.world.get_components(...) ?
    # Let's count entities with PositionComponent or just all entities
    # game_driver.game.world.entities is a set of entity IDs? No, let's check World class.

    # Checking src/yukkuri_game/engine/ecs.py might be needed, but assuming standard ECS
    # game.world.get_components(component_type) returns dict of entity_id -> component

    # Importing a component to check
    from yukkuri_game.game.yukkuri_components import YukkuriStats

    components = game_driver.game.world.get_components(YukkuriStats)
    assert len(components) == 1

    # Take a screenshot
    game_driver.save_screenshot("screenshots/test_spawn_reimu.png")
