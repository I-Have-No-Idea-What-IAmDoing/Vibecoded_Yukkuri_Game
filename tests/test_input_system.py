"""
Tests for InputSystem logic.
"""
import unittest
from unittest.mock import MagicMock
import pygame
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.game.events import PlacementStartedEvent, PlacementRequestedEvent, PlacementCancelledEvent
from yukkuri_game.game.services import InputService
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager

class TestInputSystem(unittest.TestCase):
    """
    Tests input handling logic, including placement mode and event publishing.
    """
    def setUp(self) -> None:
        """
        Sets up pygame, mocks, and the InputSystem.
        """
        # Initialize pygame for event handling
        pygame.init()

        self.yukkurrium_mock = MagicMock()
        # Mock screen_to_world to return the same coordinates passed to it
        self.yukkurrium_mock.screen_to_world.side_effect = lambda x, y, sw, sh: (float(x), float(y))

        self.input_system = InputSystem(self.yukkurrium_mock)

        self.world_mock = MagicMock(spec=World)
        self.world_mock.services = MagicMock()
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.input_service = InputService()
        self.audio_mock = MagicMock(spec=AudioManager)

        # Configure world.services
        self.world_mock.services.get.side_effect = self._get_service
        self.world_mock.services.try_get.side_effect = self._try_get_service
        self.world_mock.get_entities_with.return_value = []

        # Initialize dependencies
        self.input_system.update(self.world_mock, 0.0)
        # Also manually inject audio if update didn't catch it because try_get wasn't mocked yet
        # (Actually I added try_get mock above, so update should work if it calls try_get)

    def tearDown(self) -> None:
        """
        Cleans up pygame.
        """
        pygame.quit()

    def _get_service(self, service_type):
        if service_type == EventBus:
            return self.event_bus_mock
        elif service_type == InputService:
            return self.input_service
        return None

    def _try_get_service(self, service_type):
        if service_type == AudioManager:
            return self.audio_mock
        return None

    def test_placement_started_updates_service(self) -> None:
        """
        Tests that starting placement updates the input service state.
        """
        event = PlacementStartedEvent("reimu", 100, "yukkuri")
        self.input_system.on_placement_started(event)

        self.assertTrue(self.input_service.is_placing)
        self.assertEqual(self.input_service.place_type, "reimu")
        self.assertEqual(self.input_service.place_cost, 100)
        self.assertEqual(self.input_service.place_entity_type, "yukkuri")

    def test_left_click_emits_placement_requested(self) -> None:
        """
        Tests that left clicking while placing emits a PlacementRequestedEvent.
        """
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

    def test_right_click_cancels_placement(self) -> None:
        """
        Tests that right clicking cancels placement mode.
        """
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
