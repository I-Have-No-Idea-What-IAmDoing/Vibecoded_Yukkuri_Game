import unittest
from unittest.mock import MagicMock, patch
import pygame
import os
from datetime import datetime
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.engine.application import Application

class TestScreenshot(unittest.TestCase):
    @patch('yukkuri_game.scenes.gameplay.pygame')
    @patch('yukkuri_game.scenes.gameplay.os')
    @patch('yukkuri_game.scenes.gameplay.datetime')
    def test_take_screenshot(self, mock_datetime, mock_os, mock_pygame):
        # Setup mocks
        mock_app = MagicMock(spec=Application)
        mock_app.width = 1280
        mock_app.height = 720
        mock_screen = MagicMock()
        mock_app.screen = mock_screen

        # Instantiate Scene with mock app
        with patch('yukkuri_game.scenes.gameplay.pygame_gui.UIManager'):
             scene = GameplayScene(mock_app)

        # Mock datetime to return a fixed time
        fixed_date = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date

        # Mock os.path.exists to return False initially (so makedirs is called)
        mock_os.path.exists.return_value = False

        # Call take_screenshot
        scene.take_screenshot()

        # Verify directory creation
        mock_os.path.exists.assert_called_with("screenshots")
        mock_os.makedirs.assert_called_with("screenshots")

        # Verify save call
        expected_filename = "screenshots/screenshot_20231027_120000.png"
        mock_pygame.image.save.assert_called_with(mock_screen, expected_filename)

    @patch('yukkuri_game.scenes.gameplay.pygame')
    @patch('yukkuri_game.scenes.gameplay.os')
    @patch('yukkuri_game.scenes.gameplay.datetime')
    def test_take_screenshot_dir_exists(self, mock_datetime, mock_os, mock_pygame):
        # Setup mocks
        mock_app = MagicMock(spec=Application)
        mock_app.width = 1280
        mock_app.height = 720
        mock_screen = MagicMock()
        mock_app.screen = mock_screen

        with patch('yukkuri_game.scenes.gameplay.pygame_gui.UIManager'):
             scene = GameplayScene(mock_app)

        fixed_date = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date

        # Mock os.path.exists to return True
        mock_os.path.exists.return_value = True

        scene.take_screenshot()

        # Verify directory creation is NOT called
        mock_os.path.exists.assert_called_with("screenshots")
        mock_os.makedirs.assert_not_called()

        # Verify save call
        expected_filename = "screenshots/screenshot_20231027_120000.png"
        mock_pygame.image.save.assert_called_with(mock_screen, expected_filename)

if __name__ == '__main__':
    unittest.main()
