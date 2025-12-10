import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from yukkuri_game.engine.application import Application


class TestScreenshot(unittest.TestCase):
    @patch("yukkuri_game.engine.application.pygame")
    @patch("yukkuri_game.scenes.gameplay.pygame")  # Patch pygame used in GameplayScene
    @patch("yukkuri_game.scenes.gameplay.os")
    @patch("yukkuri_game.scenes.gameplay.datetime")
    @patch("yukkuri_game.engine.application.pygame_gui")
    @patch(
        "yukkuri_game.scenes.gameplay.pygame_gui"
    )  # Patch pygame_gui in GameplayScene to avoid font loading
    def test_take_screenshot(
        self,
        mock_pygame_gui_scene,
        mock_pygame_gui_app,
        mock_datetime,
        mock_os,
        mock_pygame_scene,
        mock_pygame_app,
    ):
        # Setup mocks
        mock_screen = MagicMock()
        # application.__init__ calls pygame.display.set_mode
        mock_pygame_app.display.set_mode.return_value = mock_screen

        # Mock datetime to return a fixed time
        fixed_date = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date
        mock_datetime.strftime = datetime.strftime

        # Mock os.path.exists to return False initially (so makedirs is called)
        mock_os.path.exists.return_value = False

        # Application needs ResourceManager.
        with (
            patch("yukkuri_game.engine.application.ResourceManager") as mock_res_mgr,
            patch(
                "yukkuri_game.engine.application.LightingEngine"
            ) as mock_lighting_engine,
        ):
            # Setup ResourceManager mock to prevent loading real data
            mock_res_mgr.return_value.load_all_data.return_value = None

            game = Application()
            game.screen = mock_screen

            # Let's mock the scene manager or just create the scene
            from yukkuri_game.scenes.gameplay import GameplayScene

            # We need to mock things inside GameplayScene.__init__/setup
            with (
                patch("yukkuri_game.scenes.gameplay.load_config"),
                patch("yukkuri_game.scenes.gameplay.Camera"),
                patch("yukkuri_game.scenes.gameplay.AudioManager"),
                patch("yukkuri_game.scenes.gameplay.PhysicsSystem"),
                patch("yukkuri_game.scenes.gameplay.GameService"),
                patch("yukkuri_game.scenes.gameplay.GameLoader") as mock_loader,
            ):
                # We need to ensure loader instance returns mocked systems if needed
                # But take_screenshot only uses pygame.image.save and os, which are patched at module level
                # So we mainly need GameplayScene instantiation to not fail.

                scene = GameplayScene(game)
                scene.take_screenshot()

            # Verify directory creation
            mock_os.path.exists.assert_called_with("screenshots")
            mock_os.makedirs.assert_called_with("screenshots")

            # Verify save call
            expected_filename = "screenshots/screenshot_20231027_120000.png"
            # GameplayScene uses its imported pygame
            mock_pygame_scene.image.save.assert_called_with(
                mock_screen, expected_filename
            )

    @patch("yukkuri_game.engine.application.pygame")
    @patch("yukkuri_game.scenes.gameplay.pygame")  # Patch pygame used in GameplayScene
    @patch("yukkuri_game.scenes.gameplay.os")
    @patch("yukkuri_game.scenes.gameplay.datetime")
    @patch("yukkuri_game.engine.application.pygame_gui")
    @patch(
        "yukkuri_game.scenes.gameplay.pygame_gui"
    )  # Patch pygame_gui in GameplayScene to avoid font loading
    def test_take_screenshot_dir_exists(
        self,
        mock_pygame_gui_scene,
        mock_pygame_gui_app,
        mock_datetime,
        mock_os,
        mock_pygame_scene,
        mock_pygame_app,
    ):
        # Setup mocks
        mock_screen = MagicMock()
        mock_pygame_app.display.set_mode.return_value = mock_screen

        fixed_date = datetime(2023, 10, 27, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date

        # Mock os.path.exists to return True
        mock_os.path.exists.return_value = True

        with (
            patch("yukkuri_game.engine.application.ResourceManager") as mock_res_mgr,
            patch(
                "yukkuri_game.engine.application.LightingEngine"
            ) as mock_lighting_engine,
        ):
            mock_res_mgr.return_value.load_all_data.return_value = None

            game = Application()
            game.screen = mock_screen

            from yukkuri_game.scenes.gameplay import GameplayScene

            with (
                patch("yukkuri_game.scenes.gameplay.load_config"),
                patch("yukkuri_game.scenes.gameplay.Camera"),
                patch("yukkuri_game.scenes.gameplay.AudioManager"),
                patch("yukkuri_game.scenes.gameplay.PhysicsSystem"),
                patch("yukkuri_game.scenes.gameplay.GameService"),
                patch("yukkuri_game.scenes.gameplay.GameLoader") as mock_loader,
            ):
                scene = GameplayScene(game)
                scene.take_screenshot()

            # Verify directory creation is NOT called
            mock_os.path.exists.assert_called_with("screenshots")
            mock_os.makedirs.assert_not_called()

            # Verify save call
            expected_filename = "screenshots/screenshot_20231027_120000.png"
            mock_pygame_scene.image.save.assert_called_with(
                mock_screen, expected_filename
            )


if __name__ == "__main__":
    unittest.main()
