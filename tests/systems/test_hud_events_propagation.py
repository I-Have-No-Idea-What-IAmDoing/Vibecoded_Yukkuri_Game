import unittest
from unittest.mock import MagicMock
import pygame
import pygame_gui
from yukkuri_game.game.ui.hud_events import HudEvents
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import TogglePauseRequest, CycleSpeedRequest

class TestHudEventsPropagation(unittest.TestCase):
    def setUp(self):
        self.layout = MagicMock()
        self.gm = MagicMock()
        self.event_bus = EventBus()
        self.hud_events = HudEvents(self.layout, self.gm, self.event_bus)

        # Mock buttons on layout
        self.layout.pause_btn = MagicMock()
        self.layout.speed_btn = MagicMock()

    def test_pause_event_propagation(self):
        # Subscribe to verify
        captured_event = None
        def on_pause(e):
            nonlocal captured_event
            captured_event = e
        self.event_bus.subscribe(TogglePauseRequest, on_pause)

        # Create mock event
        event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": self.layout.pause_btn})

        # Process event
        self.hud_events.process_event(event)

        self.assertIsNotNone(captured_event)
        self.IsInstance(captured_event, TogglePauseRequest)

    def test_speed_event_propagation(self):
        captured_event = None
        def on_speed(e):
            nonlocal captured_event
            captured_event = e
        self.event_bus.subscribe(CycleSpeedRequest, on_speed)

        event = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, {"ui_element": self.layout.speed_btn})

        self.hud_events.process_event(event)

        self.assertIsNotNone(captured_event)
        self.IsInstance(captured_event, CycleSpeedRequest)

    def IsInstance(self, obj, cls):
        """Helper because self.assertIsInstance might not be available in all unittest versions (it is though)"""
        self.assertTrue(isinstance(obj, cls))

if __name__ == '__main__':
    unittest.main()
