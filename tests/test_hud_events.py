import unittest
from unittest.mock import MagicMock
import pygame
import pygame_gui
from src.yukkuri_game.game.ui.hud_events import HudEvents
from src.yukkuri_game.game.ui.hud_layout import HudLayout
from src.yukkuri_game.game.game_manager import GameManager
from src.yukkuri_game.engine.event_bus import EventBus
from src.yukkuri_game.game.events import PlacementStartedEvent

class TestHudEvents(unittest.TestCase):
    def setUp(self):
        self.layout_mock = MagicMock(spec=HudLayout)
        self.gm_mock = MagicMock(spec=GameManager)
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.callbacks = {}

        self.hud_events = HudEvents(self.layout_mock, self.gm_mock, self.callbacks, self.event_bus_mock)

        # Setup mock buttons
        self.layout_mock.add_reimu_btn = MagicMock()
        self.layout_mock.add_cookie_btn = MagicMock()
        self.layout_mock.save_btn = MagicMock()
        self.layout_mock.load_btn = MagicMock()
        self.layout_mock.pause_btn = MagicMock()
        self.layout_mock.speed_btn = MagicMock()
        self.layout_mock.selection_window = None

    def test_add_reimu_emits_event(self):
        # Setup money
        self.gm_mock.money = 200

        event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {'ui_element': self.layout_mock.add_reimu_btn})
        self.hud_events.process_event(event)

        self.event_bus_mock.publish.assert_called_with(PlacementStartedEvent("reimu", 100, "yukkuri"))

    def test_add_cookie_emits_event(self):
        # Setup money
        self.gm_mock.money = 20

        event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {'ui_element': self.layout_mock.add_cookie_btn})
        self.hud_events.process_event(event)

        self.event_bus_mock.publish.assert_called_with(PlacementStartedEvent("cookie", 10, "item"))

if __name__ == '__main__':
    unittest.main()
