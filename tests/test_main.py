import pytest
from unittest.mock import MagicMock, patch
import sys
import yukkuri_game.main
from yukkuri_game.engine.application import Application

@pytest.fixture
def mock_pygame():
    with patch.dict('sys.modules', {'pygame': MagicMock()}):
        mock_pg = sys.modules['pygame']
        # Setup pygame structure expected by game
        mock_pg.Surface = MagicMock()
        mock_pg.event.Event = MagicMock
        mock_pg.time.Clock = MagicMock
        yield mock_pg

def test_main_headless():
    """Test the main entry point in headless mode."""
    with patch('yukkuri_game.main.Application') as MockApp, \
         patch('yukkuri_game.scenes.main_menu.pygame_gui.UIManager'), \
         patch('yukkuri_game.scenes.main_menu.pygame_gui.elements.UIButton'), \
         patch('yukkuri_game.scenes.main_menu.pygame_gui.elements.UILabel'), \
         patch('yukkuri_game.scenes.main_menu.pygame_gui.elements.UIPanel'):

        mock_instance = MockApp.return_value

        # Mock scene manager
        mock_instance.scene_manager = MagicMock()
        mock_instance.width = 1280
        mock_instance.height = 720

        with patch('argparse.ArgumentParser.parse_args') as mock_args:
            mock_args.return_value.headless = True

            from yukkuri_game.main import main
            main()

            MockApp.assert_called_with(headless=True)
            mock_instance.run.assert_called_with()
