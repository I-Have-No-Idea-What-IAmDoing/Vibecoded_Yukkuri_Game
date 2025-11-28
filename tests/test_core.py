import pytest
from unittest.mock import MagicMock, patch, ANY
import pygame
from yukkuri_game.engine.core import GameLoop

@pytest.fixture
def mock_pygame():
    with patch('yukkuri_game.engine.core.pygame') as mock_pg:
        mock_pg.display.set_mode.return_value = MagicMock()
        mock_pg.event.get.return_value = []
        mock_pg.time.Clock.return_value.tick.return_value = 16 # 16ms -> ~60fps
        yield mock_pg

@pytest.fixture
def mock_pygame_gui():
    with patch('yukkuri_game.engine.core.pygame_gui') as mock_gui:
        yield mock_gui

@pytest.fixture
def mock_resource_manager():
    with patch('yukkuri_game.engine.core.ResourceManager') as mock_rm:
        yield mock_rm

@pytest.fixture
def mock_world():
    with patch('yukkuri_game.engine.core.World') as mock_w:
        yield mock_w

def test_gameloop_init(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop(width=800, height=600, title="Test Game")

    mock_pygame.init.assert_called_once()
    mock_pygame.display.set_mode.assert_called_with((800, 600))
    mock_pygame.display.set_caption.assert_called_with("Test Game")

    assert loop.width == 800
    assert loop.height == 600
    assert loop.running is True
    assert loop.headless is False
    assert loop.time_scale == 1.0
    assert loop.paused is False

def test_set_headless(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()
    loop.set_headless(True)
    assert loop.headless is True

    loop.set_headless(False)
    assert loop.headless is False

def test_handle_events_quit(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()

    # Mock QUIT event
    quit_event = MagicMock()
    quit_event.type = pygame.QUIT
    mock_pygame.event.get.return_value = [quit_event]
    mock_pygame.QUIT = pygame.QUIT

    loop.handle_events()

    assert loop.running is False
    loop.ui_manager.process_events.assert_called_with(quit_event)

def test_tick(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()

    dt = 0.032
    loop.tick(dt)

    assert loop.dt == 0.032
    loop.ui_manager.update.assert_called_with(0.032)
    loop.world.update.assert_called_with(0.032)

def test_tick_paused(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()
    loop.paused = True

    loop.tick(0.032)

    # World update should not be called when paused
    loop.world.update.assert_not_called()

def test_tick_timescale(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()
    loop.time_scale = 2.0

    loop.tick(0.016)

    # 16ms * 2.0 = 32ms simulation time
    loop.world.update.assert_called_with(0.032)

def test_run(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()

    # Mock handle_events to stop running after one iteration
    def stop_running():
        loop.running = False

    # Mock time.get_ticks to simulate time passing
    # Initial call + 2 iterations
    mock_pygame.time.get_ticks.side_effect = [1000, 1032, 1064, 1100]

    with patch.object(loop, 'handle_events', side_effect=stop_running) as mock_handle_events, \
         patch.object(loop, 'tick') as mock_tick, \
         patch.object(loop, 'draw') as mock_draw, \
         patch.object(loop, 'setup') as mock_setup:

        loop.run()

        mock_setup.assert_called_once()
        mock_handle_events.assert_called_once()
        # tick should be called because dt (32ms) > fixed_dt (16ms)
        assert mock_tick.called
        mock_draw.assert_called_once()
        mock_pygame.quit.assert_called_once()

def test_run_headless(mock_pygame, mock_pygame_gui, mock_resource_manager, mock_world):
    loop = GameLoop()
    loop.set_headless(True)

    def stop_running():
        loop.running = False

    mock_pygame.time.get_ticks.side_effect = [1000, 1032, 1064, 1100]

    with patch.object(loop, 'handle_events', side_effect=stop_running), \
         patch.object(loop, 'tick'), \
         patch.object(loop, 'draw') as mock_draw:

        loop.run()

        mock_draw.assert_not_called()
