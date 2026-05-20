"""
Tests for InputSystem logic.

InputSystem is now a pure command producer.  Tests verify that the
correct GameCommand objects are enqueued in the InputBufferService rather
than checking for direct world mutations or event bus calls.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pygame

from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.game.commands import (
    CancelPlacementCommand,
    PlaceItemCommand,
)
from yukkuri_game.game.events import PlacementStartedEvent
from yukkuri_game.game.services import InputBufferService, InputService
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.engine.input_manager import InputManager


class TestInputSystem(unittest.TestCase):
    """
    Tests input handling logic — verifies commands are enqueued correctly.
    """

    def setUp(self) -> None:
        """Sets up pygame, mocks, and the InputSystem."""
        pygame.init()

        self.camera_mock = MagicMock()
        self.camera_mock.screen_to_world.side_effect = lambda x, y, sw, sh: (
            float(x),
            float(y),
        )

        self.input_system = InputSystem(self.camera_mock)

        self.world_mock = MagicMock(spec=World)
        self.world_mock.services = MagicMock()
        self.event_bus_mock = MagicMock(spec=EventBus)
        self.input_service = InputService()
        self.audio_mock = MagicMock(spec=AudioManager)
        self.input_manager_mock = MagicMock(spec=InputManager)
        self.buffer = InputBufferService()
        self.time_service = TimeService()

        # Configure world.services
        def get_service(service_type: type) -> object:
            if service_type == EventBus:
                return self.event_bus_mock
            if service_type == InputService:
                return self.input_service
            return None

        def try_get_service(service_type: type) -> object:
            from yukkuri_game.engine.protocols import IAudioProvider
            if service_type in (AudioManager, IAudioProvider):
                return self.audio_mock
            if service_type == InputManager:
                return self.input_manager_mock
            if service_type == InputBufferService:
                return self.buffer
            if service_type == TimeService:
                return self.time_service
            return None

        self.world_mock.services.get.side_effect = get_service
        self.world_mock.services.try_get.side_effect = try_get_service
        self.world_mock.get_entities_with.return_value = []
        self.world_mock.get_components_tuple.return_value = []

        # Default mock returns
        self.input_manager_mock.get_mouse_position.return_value = (0, 0)
        self.input_manager_mock.get_mouse_wheel.return_value = 0.0
        self.input_manager_mock.get_mouse_rel.return_value = (0, 0)
        self.input_manager_mock.is_action_just_pressed.return_value = False
        self.input_manager_mock.is_action_just_released.return_value = False
        self.input_manager_mock.is_action_pressed.return_value = False

        # Initialize dependencies
        with patch("pygame.display.get_surface") as mock_surface:
            mock_surface.return_value.get_size.return_value = (800, 600)
            self.input_system.update(self.world_mock, 0.0)

    def tearDown(self) -> None:
        """Cleans up pygame."""
        pygame.quit()

    # ------------------------------------------------------------------
    # Mode-state tests (these don't need the buffer)
    # ------------------------------------------------------------------

    def test_placement_started_updates_service(self) -> None:
        """PlacementStartedEvent updates the InputService state."""
        event = PlacementStartedEvent("reimu", 100, "yukkuri")
        self.input_system.on_placement_started(event)

        self.assertTrue(self.input_service.is_placing)
        self.assertEqual(self.input_service.place_type, "reimu")
        self.assertEqual(self.input_service.place_cost, 100)
        self.assertEqual(self.input_service.place_entity_type, "yukkuri")

    # ------------------------------------------------------------------
    # Command-queue tests
    # ------------------------------------------------------------------

    def test_left_click_enqueues_place_item_command(self) -> None:
        """Left clicking while placing enqueues a PlaceItemCommand."""
        self.input_service.start_placement("reimu", 100, "yukkuri")

        self.input_manager_mock.get_mouse_position.return_value = (100, 100)
        self.input_manager_mock.is_action_just_pressed.side_effect = (
            lambda action: action == "select"
        )

        with patch("pygame.display.get_surface") as mock_get_surface:
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            mock_get_surface.return_value = mock_surface
            self.input_system.update(self.world_mock, 0.0)

        commands = self.buffer.pop_all()
        place_cmds = [c for c in commands if isinstance(c, PlaceItemCommand)]
        self.assertEqual(len(place_cmds), 1)
        cmd = place_cmds[0]
        self.assertEqual(cmd.place_type, "reimu")
        self.assertEqual(cmd.cost, 100)
        self.assertEqual(cmd.entity_type, "yukkuri")

        # Placement mode should be cancelled immediately (no shift)
        self.assertFalse(self.input_service.is_placing)

    def test_right_click_enqueues_cancel_placement_command(self) -> None:
        """Right clicking during placement enqueues a CancelPlacementCommand."""
        self.input_service.start_placement("reimu", 100, "yukkuri")

        self.input_manager_mock.get_mouse_position.return_value = (100, 100)
        self.input_manager_mock.is_action_just_pressed.side_effect = (
            lambda action: action == "cancel_action"
        )

        with patch("pygame.display.get_surface") as mock_get_surface:
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            mock_get_surface.return_value = mock_surface
            self.input_system.update(self.world_mock, 0.0)

        commands = self.buffer.pop_all()
        cancel_cmds = [c for c in commands if isinstance(c, CancelPlacementCommand)]
        self.assertEqual(len(cancel_cmds), 1)

    def test_time_speed_blocked_by_ctrl(self) -> None:
        """Time speed commands are NOT enqueued when Ctrl is held."""
        from yukkuri_game.game.commands import TimeSpeedCommand

        self.input_manager_mock.is_action_just_pressed.side_effect = (
            lambda action: action == "time_speed_up"
        )
        self.input_manager_mock.is_action_pressed.side_effect = (
            lambda action: action == "ctrl"
        )

        with patch("pygame.display.get_surface") as mock_get_surface:
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            mock_get_surface.return_value = mock_surface
            self.input_system.update(self.world_mock, 0.0)

        commands = self.buffer.pop_all()
        speed_cmds = [c for c in commands if isinstance(c, TimeSpeedCommand)]
        self.assertEqual(len(speed_cmds), 0)

    def test_time_speed_enqueued_without_ctrl(self) -> None:
        """Time speed command IS enqueued when Ctrl is not held."""
        from yukkuri_game.game.commands import TimeSpeedCommand

        # ecs_world needed for TimeService lookup in _handle_time_controls
        self.input_system.ecs_world = self.world_mock

        self.input_manager_mock.is_action_just_pressed.side_effect = (
            lambda action: action == "time_speed_up"
        )
        self.input_manager_mock.is_action_pressed.return_value = False

        with patch("pygame.display.get_surface") as mock_get_surface:
            mock_surface = MagicMock()
            mock_surface.get_size.return_value = (800, 600)
            mock_get_surface.return_value = mock_surface
            self.input_system.update(self.world_mock, 0.0)

        commands = self.buffer.pop_all()
        speed_cmds = [c for c in commands if isinstance(c, TimeSpeedCommand)]
        self.assertEqual(len(speed_cmds), 1)
        # Initial speed 1.0 doubled = 2.0
        self.assertAlmostEqual(speed_cmds[0].speed_multiplier, 2.0)


if __name__ == "__main__":
    unittest.main()
