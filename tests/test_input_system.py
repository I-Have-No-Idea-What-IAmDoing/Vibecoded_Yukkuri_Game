import unittest
from unittest.mock import MagicMock
import pygame
from src.yukkuri_game.game.input_system import InputSystem
from src.yukkuri_game.game.events import PlacementStartedEvent, PlacementRequestedEvent, PlacementCancelledEvent
from src.yukkuri_game.game.services import InputService
from src.yukkuri_game.engine.event_bus import EventBus
from src.yukkuri_game.engine.ecs import World

class TestInputSystem(unittest.TestCase):
    def setUp(self):
        self.yukkurrium_mock = MagicMock()
        # Mock screen_to_world to return the same coordinates passed to it
        self.yukkurrium_mock.screen_to_world.side_effect = lambda x, y, sw, sh: (float(x), float(y))

        self.input_system = InputSystem(self.yukkurrium_mock)

        self.world_mock = MagicMock(spec=World)
        self.world_mock.services = MagicMock()
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.input_service = InputService()

        # Configure world.services
        self.world_mock.services.get.side_effect = self._get_service
        self.world_mock.get_entities_with.return_value = []

        # Initialize dependencies
        self.input_system.update(self.world_mock, 0.0)

    def _get_service(self, service_type):
        if service_type == EventBus:
            return self.event_bus_mock
        elif service_type == InputService:
            return self.input_service
        return None

    def test_placement_started_updates_service(self):
        event = PlacementStartedEvent("reimu", 100, "yukkuri")
        self.input_system.on_placement_started(event)

        self.assertTrue(self.input_service.is_placing)
        self.assertEqual(self.input_service.place_type, "reimu")
        self.assertEqual(self.input_service.place_cost, 100)
        self.assertEqual(self.input_service.place_entity_type, "yukkuri")

    def test_left_click_emits_placement_requested(self):
        # Start placement
        self.input_service.start_placement("reimu", 100, "yukkuri")

        # Simulate click
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (100, 100)})
        self.input_system.handle_event(event, self.world_mock, 800, 600)

        # Check event published
        self.event_bus_mock.publish.assert_called_with(
            PlacementRequestedEvent(100.0, 100.0, "reimu", 100, "yukkuri")
        )

        # Check placement reset
        self.assertFalse(self.input_service.is_placing)

    def test_right_click_cancels_placement(self):
        # Start placement
        self.input_service.start_placement("reimu", 100, "yukkuri")

        # Simulate right click
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (100, 100)})
        self.input_system.handle_event(event, self.world_mock, 800, 600)

        # Check event published
        self.event_bus_mock.publish.assert_called_with(
            PlacementCancelledEvent()
        )

        # Check placement reset
        self.assertFalse(self.input_service.is_placing)

if __name__ == '__main__':
    unittest.main()
