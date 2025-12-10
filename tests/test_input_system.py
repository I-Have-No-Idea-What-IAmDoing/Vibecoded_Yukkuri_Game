"""
Tests for InputSystem logic.
"""

import unittest
from unittest.mock import MagicMock, patch
import pygame
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.game.events import (
    PlacementStartedEvent,
    PlacementRequestedEvent,
    PlacementCancelledEvent,
)
from yukkuri_game.game.services import InputService
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.engine.input_manager import InputManager


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
        self.yukkurrium_mock.screen_to_world.side_effect = lambda x, y, sw, sh: (
            float(x),
            float(y),
        )

        self.input_system = InputSystem(self.yukkurrium_mock)

        self.world_mock = MagicMock(spec=World)
        self.world_mock.services = MagicMock()
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.input_service = InputService()
        self.audio_mock = MagicMock(spec=AudioManager)
        self.input_manager_mock = MagicMock(spec=InputManager)

        # Configure world.services
        def get_service(service_type):
            if service_type == EventBus:
                return self.event_bus_mock
            if service_type == InputService:
                return self.input_service
            return None

        def try_get_service(service_type):
            if service_type == AudioManager:
                return self.audio_mock
            if service_type == InputManager:
                return self.input_manager_mock
            return None

        self.world_mock.services.get.side_effect = get_service
        self.world_mock.services.try_get.side_effect = try_get_service
        self.world_mock.get_entities_with.return_value = []

        # Default mock returns
        self.input_manager_mock.get_mouse_position.return_value = (0, 0)
        self.input_manager_mock.is_action_just_pressed.return_value = False
        self.input_manager_mock.is_action_just_released.return_value = False

        # Initialize dependencies
        # Need to mock display.get_surface for update()
        with patch("pygame.display.get_surface") as mock_surface:
            mock_surface.return_value.get_size.return_value = (800, 600)
            self.input_system.update(self.world_mock, 0.0)

    def tearDown(self) -> None:
        """
        Cleans up pygame.
        """
        pygame.quit()

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

        # Mock Input
        self.input_manager_mock.get_mouse_position.return_value = (100, 100)
        # Simulate Select Pressed
        self.input_manager_mock.is_action_just_pressed.side_effect = (
            lambda action: action == "select"
        )

        with patch("pygame.display.get_surface") as mock_get_surface:
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            mock_get_surface.return_value = mock_surface

            self.input_system.update(self.world_mock, 0.0)

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

        # Mock Input
        self.input_manager_mock.get_mouse_position.return_value = (100, 100)
        # Simulate Cancel Pressed
        self.input_manager_mock.is_action_just_pressed.side_effect = (
            lambda action: action == "cancel_action"
        )

        with patch("pygame.display.get_surface") as mock_get_surface:
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            mock_get_surface.return_value = mock_surface

            self.input_system.update(self.world_mock, 0.0)

        # Check event published
        self.event_bus_mock.publish.assert_called_with(PlacementCancelledEvent())

        # Check placement reset
        self.assertFalse(self.input_service.is_placing)


if __name__ == "__main__":
    unittest.main()
