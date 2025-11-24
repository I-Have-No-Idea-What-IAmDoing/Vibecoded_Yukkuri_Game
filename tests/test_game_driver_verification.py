import pytest
import os
import pygame
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.testing.environment import TestEnvironment
from yukkuri_game.testing.predicates import WaitFrames, InjectInput, WaitUntil
from yukkuri_game.testing.input_helpers import Click, KeyPress
from yukkuri_game.main import YukkuriGame
from yukkuri_game.engine.core import GameLoop

def test_driver_verification():
    """
    Verifies that the GameDriver can run a simple scenario.
    """

    # Define a simple scenario
    def simple_scenario(game):
        # Wait for a few frames to let things settle
        yield WaitFrames(5)

        # Inject a mouse click using the proposed syntax
        yield InjectInput(Click(100, 100))

        # Wait until some time passes
        yield WaitUntil(lambda: game.gm.time_elapsed > 0.1, timeout=5.0)

        # Verify state
        assert game.gm.time_elapsed > 0.0

    # Run the test
    with TestEnvironment() as env:
        game = YukkuriGame()
        driver = GameDriver(game)
        # setup() is crucial: it initializes Pygame and sets headless mode
        driver.setup()

        try:
            driver.run_scenario(simple_scenario(game))
        finally:
            driver.cleanup()

if __name__ == "__main__":
    test_driver_verification()
