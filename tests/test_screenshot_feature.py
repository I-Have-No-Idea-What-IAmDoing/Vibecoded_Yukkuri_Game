import unittest
from unittest.mock import MagicMock, patch
import pygame
import os
from datetime import datetime
from src.yukkuri_game.main import YukkuriGame

class TestScreenshot(unittest.TestCase):
    @patch('src.yukkuri_game.main.pygame')
    @patch('src.yukkuri_game.main.os')
    @patch('src.yukkuri_game.main.datetime')
    @patch('src.yukkuri_game.engine.core.pygame')
    @patch('src.yukkuri_game.engine.core.pygame_gui')
    def test_take_screenshot(self, mock_pygame_gui_core, mock_pygame_core, mock_datetime, mock_os, mock_pygame_main):
        # Setup mocks
        mock_screen = MagicMock()
        mock_pygame_core.display.set_mode.return_value = mock_screen

        # Mock datetime to return a fixed time
        fixed_date = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date
        mock_datetime.strftime = datetime.strftime

        # Mock os.path.exists to return False initially (so makedirs is called)
        mock_os.path.exists.return_value = False

        # Create game instance
        # We need to patch GameLoop.__init__ or ensure it doesn't fail
        # GameLoop.__init__ calls pygame.init, pygame.display.set_mode, ResourceManager, etc.
        # We might need to mock more things if YukkuriGame instantiation is complex.

        # Let's try to instantiate. We mocked pygame in main and core.
        with patch('src.yukkuri_game.engine.core.ResourceManager') as mock_res_mgr, \
             patch('src.yukkuri_game.engine.core.World') as mock_world:

            game = YukkuriGame()
            # Manually set screen because __init__ sets it from pygame.display.set_mode
            game.screen = mock_screen

            # Call take_screenshot
            game.take_screenshot()

            # Verify directory creation
            mock_os.path.exists.assert_called_with("screenshots")
            mock_os.makedirs.assert_called_with("screenshots")

            # Verify save call
            expected_filename = "screenshots/screenshot_20231027_120000.png"
            # Note: we are checking if mock_pygame_main.image.save was called.
            # Since we mocked 'src.yukkuri_game.main.pygame', game.take_screenshot uses that mock.
            mock_pygame_main.image.save.assert_called_with(mock_screen, expected_filename)

    @patch('src.yukkuri_game.main.pygame')
    @patch('src.yukkuri_game.main.os')
    @patch('src.yukkuri_game.main.datetime')
    @patch('src.yukkuri_game.engine.core.pygame')
    @patch('src.yukkuri_game.engine.core.pygame_gui')
    def test_take_screenshot_dir_exists(self, mock_pygame_gui_core, mock_pygame_core, mock_datetime, mock_os, mock_pygame_main):
        # Setup mocks
        mock_screen = MagicMock()
        mock_pygame_core.display.set_mode.return_value = mock_screen

        fixed_date = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date

        # Mock os.path.exists to return True
        mock_os.path.exists.return_value = True

        with patch('src.yukkuri_game.engine.core.ResourceManager'), \
             patch('src.yukkuri_game.engine.core.World'):

            game = YukkuriGame()
            game.screen = mock_screen

            game.take_screenshot()

            # Verify directory creation is NOT called
            mock_os.path.exists.assert_called_with("screenshots")
            mock_os.makedirs.assert_not_called()

            # Verify save call
            expected_filename = "screenshots/screenshot_20231027_120000.png"
            mock_pygame_main.image.save.assert_called_with(mock_screen, expected_filename)

if __name__ == '__main__':
    unittest.main()
