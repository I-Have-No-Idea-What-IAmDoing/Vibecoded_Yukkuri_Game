import pytest
from unittest.mock import MagicMock, patch
import sys
import importlib
import yukkuri_game.main


@pytest.fixture
def mock_pygame():
    with patch.dict("sys.modules", {"pygame": MagicMock()}):
        mock_pg = sys.modules["pygame"]
        # Setup pygame structure expected by game
        mock_pg.Surface = MagicMock()
        mock_pg.event.Event = MagicMock
        mock_pg.time.Clock = MagicMock
        yield mock_pg


@pytest.fixture
def yukkuri_game_headless(mock_pygame):
    # Use real logic for internal systems to ensure integration.

    with (
        patch("yukkuri_game.engine.audio.AudioManager"),
        patch("yukkuri_game.game.services.PersistenceService"),
        patch("yukkuri_game.game.input_system.InputSystem"),
        patch("yukkuri_game.game.camera.Camera"),
    ):
        with patch("yukkuri_game.engine.resource_manager.ResourceManager") as MockRM:
            # Configure mock instance
            mock_rm_instance = MockRM.return_value
            mock_rm_instance.yukkuri_types = {
                "reimu": {"image": "reimu.png", "width": 32, "height": 32}
            }
            mock_rm_instance.item_types = {}
            mock_rm_instance.tuning = MagicMock()
            mock_rm_instance.load_image.return_value = (
                MagicMock()
            )  # Return mock surface

            # Reload main module to pick up patched classes in imports
            importlib.reload(yukkuri_game.main)
            from yukkuri_game.engine.application import Application as ReloadedGame

            game = ReloadedGame(headless=True)
            return game


def test_game_initialization(yukkuri_game_headless):
    """Test that the game initializes correctly in headless mode."""
    assert yukkuri_game_headless.headless is True
    assert yukkuri_game_headless.scene_manager is not None


def test_game_update(yukkuri_game_headless):
    """Test the main update loop."""
    # Mock scene manager
    yukkuri_game_headless.scene_manager = MagicMock()

    # Application update takes dt
    yukkuri_game_headless.update(0.016)

    # Verify update calls scene_manager.update
    yukkuri_game_headless.scene_manager.update.assert_called_with(0.016)


def test_main_headless():
    """Test the main entry point in headless mode."""
    # We need to ensure main imports YukkuriGame which matches what we expect

    with (
        patch("yukkuri_game.main.Application") as MockApp,
        patch("yukkuri_game.scenes.main_menu.pygame_gui") as mock_gui,
    ):  # Patch GUI in MainMenu
        mock_instance = MockApp.return_value

        with patch("argparse.ArgumentParser.parse_args") as mock_args:
            mock_args.return_value.headless = True

            from yukkuri_game.main import main

            # We don't reload here because we want to test the 'main' function as is,
            # but patching 'yukkuri_game.main.YukkuriGame' should work.
            main()

            MockApp.assert_called_with(headless=True)
            mock_instance.run.assert_called_with()
