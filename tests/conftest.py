import pytest
import sys
import os
from yukkuri_game.main import YukkuriGame
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.testing.environment import TestEnvironment

# Add the project root to sys.path so src can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture
def game_driver():
    with TestEnvironment():
        game = YukkuriGame()
        driver = GameDriver(game)
        yield driver
        # Teardown is handled by driver.cleanup()
        driver.cleanup()
