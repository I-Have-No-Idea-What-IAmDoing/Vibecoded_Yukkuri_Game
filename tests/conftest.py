"""
Pytest configuration and shared fixtures for the test suite.
"""
import pytest
import sys
import os
import pygame
from yukkuri_game.main import YukkuriGame
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.testing.environment import TestEnvironment

# Add the project root to sys.path so src can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture
def game_driver() -> GameDriver:
    """
    Fixture that yields a GameDriver controlling a fresh YukkuriGame
    inside a headless environment.

    The environment is configured to use dummy video/audio drivers to run
    without a display.

    Returns:
        GameDriver: A driver instance for controlling the game.
    """
    with TestEnvironment():
        # Initialize game in headless mode
        game = YukkuriGame(headless=True)

        # Note: Render system init is handled lazily by GameDriver/YukkuriGame
        # when needed (e.g. for screenshots), after game.setup() is called
        # by the driver.

        driver = GameDriver(game)
        driver.seed_rng(42) # Default deterministic seed
        yield driver

        # Cleanup
        driver.cleanup()
        pygame.quit()
