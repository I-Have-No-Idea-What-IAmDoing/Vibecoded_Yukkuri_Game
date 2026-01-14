"""
Pytest configuration and shared fixtures for the test suite.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# 1. Setup Path
# Add the project root to sys.path so src can be imported
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

# 2. Mock Dependencies (Pygame)
# Attempt to mock pygame if not installed (for headless CI/Test envs)
try:
    import pygame
except ImportError:
    mock_pygame = MagicMock()
    sys.modules["pygame"] = mock_pygame
    sys.modules["pygame.locals"] = MagicMock()
    sys.modules["pygame.key"] = MagicMock()
    sys.modules["pygame.time"] = MagicMock()
    sys.modules["pygame.display"] = MagicMock()
    sys.modules["pygame.event"] = MagicMock()
    sys.modules["pygame.image"] = MagicMock()
    sys.modules["pygame.rect"] = MagicMock()
    sys.modules["pygame.font"] = MagicMock()
    sys.modules["pygame.mixer"] = MagicMock()
    sys.modules["pygame.transform"] = MagicMock()
    sys.modules["pygame.draw"] = MagicMock()

    # Also mock pygame dependants that might fail import
    sys.modules["pygame_gui"] = MagicMock()
    sys.modules["pygame_light2d"] = MagicMock()
    
    # We still need to import it to make it available as 'pygame' in this module scope if it wasn't already
    import pygame

# 3. Project Imports
from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.testing.environment import TestEnvironment


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
        game = Application(headless=True)

        # Note: Render system init is handled lazily by GameDriver/YukkuriGame
        # when needed (e.g. for screenshots), after game.setup() is called
        # by the driver.

        driver = GameDriver(game)
        # Ensure the driver is set up (this pushes the initial scene)
        driver.setup()
        yield driver

        # Cleanup
        driver.cleanup()
        pygame.quit()
