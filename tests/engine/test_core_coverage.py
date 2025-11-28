import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.engine.core import GameLoop
from yukkuri_game.engine.ecs import World
import pygame

class TestGameLoop:
    @pytest.fixture
    def mock_pygame(self):
        with patch('yukkuri_game.engine.core.pygame') as mock:
            mock.event.get.return_value = []
            mock.time.Clock.return_value.tick.return_value = 16
            yield mock

    @pytest.fixture
    def mock_pygame_gui(self):
        with patch('yukkuri_game.engine.core.pygame_gui') as mock:
            yield mock

    @pytest.fixture
    def mock_resource_manager(self):
        with patch('yukkuri_game.engine.core.ResourceManager') as mock:
            yield mock

    def test_initialization(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop(width=800, height=600, title="Test Game")

        assert game.width == 800
        assert game.height == 600
        assert game.running is True
        assert game.headless is False
        assert game.time_scale == 1.0
        assert game.paused is False

        mock_pygame.init.assert_called_once()
        mock_pygame.display.set_mode.assert_called_with((800, 600))
        mock_pygame.display.set_caption.assert_called_with("Test Game")
        mock_resource_manager.return_value.load_all_data.assert_called_once()

    def test_handle_events_quit(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop()

        # Mock QUIT event
        quit_event = MagicMock()
        quit_event.type = pygame.QUIT

        # IMPORTANT: GameLoop imports pygame inside the file.
        # The pygame.QUIT in core.py is not the same object as pygame.QUIT in the test
        # if we are not careful about how patching works or if we use the value.
        # However, since we patched `yukkuri_game.engine.core.pygame`, the module usage
        # inside core.py refers to our mock.

        # Set the mock's QUIT attribute to match our test value if needed,
        # or use the value from the patched module.
        mock_pygame.QUIT = pygame.QUIT

        mock_pygame.event.get.return_value = [quit_event]

        game.handle_events()

        assert game.running is False
        game.ui_manager.process_events.assert_called_with(quit_event)

    def test_update(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop()
        game.paused = False
        game.time_scale = 2.0
        # game.dt is set inside tick based on argument, usually.
        # The new loop uses tick(dt).

        # Mock World update
        game.world = MagicMock(spec=World)

        game.tick(0.016)

        # Check if world update was called with simulated dt
        game.world.update.assert_called_with(0.016 * 2.0)
        # Check UI update
        game.ui_manager.update.assert_called_with(0.016)

    def test_update_paused(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop()
        game.paused = True
        game.world = MagicMock(spec=World)

        game.tick(0.016)

        game.ui_manager.update.assert_called_with(0.016)
        # World should NOT be updated if paused
        game.world.update.assert_not_called()
        game.world.update.assert_not_called()

    def test_draw(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop()
        game.render_world = MagicMock()

        game.draw()

        game.screen.fill.assert_called_with((30, 30, 30))
        game.render_world.assert_called_once()
        game.ui_manager.draw_ui.assert_called_with(game.screen)
        mock_pygame.display.flip.assert_called_once()

    def test_run_headless(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop()
        game.set_headless(True)
        game.setup = MagicMock()

        # Run for one iteration
        def stop_loop():
            game.running = False

        game.handle_events = MagicMock(side_effect=stop_loop)
        # Mock tick instead of update, as run loop calls tick
        game.tick = MagicMock()
        game.draw = MagicMock()

        # Mock time
        # Return floats for get_ticks (ms)
        mock_pygame.time.get_ticks.side_effect = [0, 1000] # Start at 0, next loop at 1s (1000ms)

        game.run()

        game.setup.assert_called_once()
        game.handle_events.assert_called()
        game.tick.assert_called()
        game.draw.assert_not_called()
        mock_pygame.quit.assert_called_once()

    def test_set_headless(self, mock_pygame, mock_pygame_gui, mock_resource_manager):
        game = GameLoop()
        game.set_headless(True)
        assert game.headless is True
        game.set_headless(False)
        assert game.headless is False
