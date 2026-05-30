import pytest
import os
import pygame
from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver


def test_headless_mode(game_driver: GameDriver, tmp_path):
    """
    Verifies that the headless mode infrastructure works correctly.
    """
    game = game_driver.game
    assert isinstance(game, Application)
    assert game.headless is True
    assert game.lights_engine is None

    # Verify initial state
    assert game_driver.simulated_time == 0.0

    # Verify scene is active (setup called in fixture)
    assert game.scene_manager.current_scene is not None

    # Run a few ticks
    game_driver.run_for(1.0)

    # Verify time advanced
    assert game_driver.simulated_time >= 1.0
    assert game_driver.frame_count > 0

    # Test Screenshot capability
    screenshot_path = str(tmp_path / "headless_test.png")
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)

    game_driver.save_screenshot(screenshot_path)

    assert os.path.exists(screenshot_path)
    # Check that file is not empty
    assert os.path.getsize(screenshot_path) > 0

    # Optional: Load image to verify it's a valid image
    try:
        img = pygame.image.load(screenshot_path)
        assert img.get_width() == game.width
        assert img.get_height() == game.height
    except pygame.error:
        pytest.fail("Screenshot is not a valid image")
    finally:
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
