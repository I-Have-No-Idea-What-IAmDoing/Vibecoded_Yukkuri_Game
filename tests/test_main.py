import pytest
from unittest.mock import MagicMock, patch
import pygame
import os
import sys
import importlib
import yukkuri_game.main
from yukkuri_game.main import YukkuriGame

@pytest.fixture
def mock_pygame():
    with patch.dict('sys.modules', {'pygame': MagicMock()}):
        mock_pg = sys.modules['pygame']
        # Setup pygame structure expected by game
        mock_pg.Surface = MagicMock()
        mock_pg.event.Event = MagicMock
        mock_pg.time.Clock = MagicMock
        yield mock_pg

@pytest.fixture
def mock_game_loop():
    with patch('yukkuri_game.engine.core.GameLoop') as mock_gl:
        pass

@pytest.fixture
def yukkuri_game_headless(mock_pygame):
    # Use real logic for internal systems to ensure integration.

    with patch('yukkuri_game.engine.audio.AudioManager'), \
         patch('yukkuri_game.game.services.PersistenceService'), \
         patch('yukkuri_game.game.input_system.InputSystem'), \
         patch('yukkuri_game.main.load_config') as mock_load_config, \
         patch('yukkuri_game.game.yukkurrium.Yukkurrium'):

        with patch('yukkuri_game.engine.resource_manager.ResourceManager') as MockRM:
            # Configure mock instance
            mock_rm_instance = MockRM.return_value
            mock_rm_instance.yukkuri_types = {"reimu": {"image": "reimu.png", "width": 32, "height": 32}}
            mock_rm_instance.item_types = {}
            mock_rm_instance.tuning = MagicMock()
            mock_rm_instance.load_image.return_value = MagicMock() # Return mock surface

            # Reload main module to pick up patched classes in imports
            importlib.reload(yukkuri_game.main)
            from yukkuri_game.main import YukkuriGame as ReloadedGame

            # Mock config
            mock_config = MagicMock()
            mock_config.world.width = 1000
            mock_config.world.height = 1000
            mock_config.rules.stat_decay = MagicMock()
            mock_config.rules.lifecycle = MagicMock()
            mock_load_config.return_value = mock_config

            game = ReloadedGame()
            game.set_headless(True)
            game.setup()
            return game

def test_game_initialization(yukkuri_game_headless):
    """Test that the game initializes correctly in headless mode."""
    assert yukkuri_game_headless.headless is True
    assert yukkuri_game_headless.gm is not None
    assert yukkuri_game_headless.yukkurrium is not None

def test_game_update(yukkuri_game_headless):
    """Test the main update loop."""
    yukkuri_game_headless.dt = 0.016
    yukkuri_game_headless.time_scale = 1.0
    yukkuri_game_headless.paused = False

    # Mock GM time elapsed update
    yukkuri_game_headless.gm.time_elapsed = 0.0

    # Test tick() instead of update()
    with patch('yukkuri_game.engine.core.GameLoop.tick'):
        yukkuri_game_headless.tick(0.016)

        # Check if GM time was updated
        assert yukkuri_game_headless.gm.time_elapsed > 0.0

        # Check if systems updated
        yukkuri_game_headless.yukkurrium.update.assert_called_once()

def test_game_update_paused(yukkuri_game_headless):
    """Test that time doesn't advance when paused."""
    yukkuri_game_headless.dt = 0.016
    yukkuri_game_headless.paused = True
    yukkuri_game_headless.gm.time_elapsed = 10.0

    with patch('yukkuri_game.engine.core.GameLoop.tick'):
        yukkuri_game_headless.tick(0.016)

        assert yukkuri_game_headless.gm.time_elapsed == 10.0

def test_toggle_pause(yukkuri_game_headless):
    """Test toggling pause."""
    yukkuri_game_headless.paused = False

    # EventBus is REAL now. We can subscribe a mock listener to verify.
    mock_listener = MagicMock()
    from yukkuri_game.game.events import GamePausedEvent
    yukkuri_game_headless.event_bus.subscribe(GamePausedEvent, mock_listener)

    yukkuri_game_headless.toggle_pause()
    assert yukkuri_game_headless.paused is True
    mock_listener.assert_called()

    yukkuri_game_headless.toggle_pause()
    assert yukkuri_game_headless.paused is False

def test_cycle_speed(yukkuri_game_headless):
    """Test cycling game speed."""
    yukkuri_game_headless.time_scale = 1.0

    # Mock HUD since it's accessed in cycle_speed
    yukkuri_game_headless.hud = MagicMock()

    yukkuri_game_headless.cycle_speed()
    assert yukkuri_game_headless.time_scale == 2.0

    yukkuri_game_headless.cycle_speed()
    assert yukkuri_game_headless.time_scale == 5.0

    yukkuri_game_headless.cycle_speed()
    assert yukkuri_game_headless.time_scale == 0.5

    yukkuri_game_headless.cycle_speed()
    assert yukkuri_game_headless.time_scale == 1.0

def test_take_screenshot(yukkuri_game_headless):
    """Test taking a screenshot."""

    # Access the global mock from sys.modules['pygame']
    mock_pg = sys.modules['pygame']

    with patch('os.makedirs') as mock_makedirs, \
         patch('os.path.exists', return_value=False):

        yukkuri_game_headless.screen = MagicMock()
        yukkuri_game_headless.take_screenshot()

        mock_makedirs.assert_called_with("screenshots")
        mock_pg.image.save.assert_called()

def test_main_headless():
    """Test the main entry point in headless mode."""
    # We need to ensure main imports YukkuriGame which matches what we expect

    with patch('yukkuri_game.main.YukkuriGame') as MockGame:
        mock_instance = MockGame.return_value

        with patch('argparse.ArgumentParser.parse_args') as mock_args:
            mock_args.return_value.headless = True

            from yukkuri_game.main import main
            # We don't reload here because we want to test the 'main' function as is,
            # but patching 'yukkuri_game.main.YukkuriGame' should work.
            main()

            MockGame.assert_called_with(headless=True)
            mock_instance.run.assert_called_with()
