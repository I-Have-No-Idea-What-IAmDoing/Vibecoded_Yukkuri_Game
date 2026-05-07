"""
UI event integration tests — adapted for command-buffer architecture.

Events (EntitySelectedEvent, PlacementRequestedEvent, etc.) are now
published by GameCommand.execute(), not directly by InputSystem.
To observe them, tests must:
  1. Call system.update() → commands are enqueued in InputBufferService
  2. Drain and execute commands to publish the events
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import (
    EntitySelectedEvent,
    PlacementRequestedEvent,
)
from yukkuri_game.game.components import Transform, Selectable
from yukkuri_game.game.services import InputBufferService, InputService
from yukkuri_game.engine.input_manager import InputManager


def _drain_and_execute(buf: InputBufferService, world: World) -> None:
    """Execute all commands currently in the buffer against the world."""
    for cmd in buf.pop_all():
        if hasattr(cmd, "execute"):
            cmd.execute(world)


class TestUIEvents(unittest.TestCase):
    def setUp(self) -> None:
        self.world = World()
        self.yukkurrium = MagicMock()
        self.system = InputSystem(self.yukkurrium)

        # Real EventBus so subscribers fire
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        # InputService
        self.input_service = InputService()
        self.world.services.register(self.input_service)

        # InputBufferService — required by InputSystem to enqueue commands
        self.buf = InputBufferService()
        self.world.services.register(self.buf, InputBufferService)

        # InputManager mock
        self.input_manager = MagicMock(spec=InputManager)
        self.world.services.register(self.input_manager, InputManager)

        self.yukkurrium.screen_to_world.return_value = (0, 0)

        self.input_manager.get_mouse_position.return_value = (0, 0)
        self.input_manager.get_mouse_wheel.return_value = 0.0
        self.input_manager.get_mouse_rel.return_value = (0, 0)
        self.input_manager.is_action_just_pressed.return_value = False
        self.input_manager.is_action_just_released.return_value = False
        self.input_manager.is_action_pressed.return_value = False

        self.patcher = patch(
            "yukkuri_game.game.input_system.pygame.display.get_surface"
        )
        self.mock_get_surface = self.patcher.start()
        mock_surface = MagicMock()
        mock_surface.get_size.return_value = (800, 600)
        self.mock_get_surface.return_value = mock_surface

        # Init lazy deps
        self.system.update(self.world, 0.0)

    def tearDown(self) -> None:
        self.patcher.stop()

    @patch("pygame.key.get_pressed")
    def test_entity_selection_event(self, mock_get_pressed: MagicMock) -> None:
        """Clicking an entity then releasing fires an EntitySelectedEvent."""
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = False
        mock_get_pressed.return_value = mock_keys

        self.input_manager.get_mouse_position.return_value = (100, 100)
        self.yukkurrium.screen_to_world.return_value = (100, 100)

        entity_id = self.world.create_entity(
            Transform(x=100, y=100), Selectable()
        )

        captured_event = None

        def on_selected(e: EntitySelectedEvent) -> None:
            nonlocal captured_event
            captured_event = e

        self.event_bus.subscribe(EntitySelectedEvent, on_selected)

        # Frame 1: press — starts drag
        self.input_manager.is_action_just_pressed.side_effect = (
            lambda a: a == "select"
        )
        self.system.update(self.world, 0.1)
        _drain_and_execute(self.buf, self.world)
        self.assertIsNotNone(self.system.drag_start_pos)

        # Frame 2: release — enqueues SelectEntitiesCommand
        self.input_manager.is_action_just_pressed.return_value = False
        self.input_manager.is_action_just_pressed.side_effect = None
        self.input_manager.is_action_just_released.side_effect = (
            lambda a: a == "select"
        )
        self.system.update(self.world, 0.1)
        _drain_and_execute(self.buf, self.world)

        self.assertIsNotNone(captured_event)
        self.assertIsInstance(captured_event, EntitySelectedEvent)
        self.assertIn(entity_id, captured_event.entity_ids)

    @patch("pygame.key.get_pressed")
    def test_entity_deselection_event(self, mock_get_pressed: MagicMock) -> None:
        """Clicking empty space fires EntitySelectedEvent with empty ids."""
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = False
        mock_get_pressed.return_value = mock_keys

        # Click far from any entity
        self.input_manager.get_mouse_position.return_value = (500, 500)
        self.yukkurrium.screen_to_world.return_value = (500, 500)

        entity_id = self.world.create_entity(
            Transform(x=100, y=100), Selectable(selected=True)
        )

        captured_event = None

        def on_selected(e: EntitySelectedEvent) -> None:
            nonlocal captured_event
            captured_event = e

        self.event_bus.subscribe(EntitySelectedEvent, on_selected)

        # Frame 1: press
        self.input_manager.is_action_just_pressed.side_effect = (
            lambda a: a == "select"
        )
        self.system.update(self.world, 0.1)
        _drain_and_execute(self.buf, self.world)

        # Frame 2: release
        self.input_manager.is_action_just_pressed.return_value = False
        self.input_manager.is_action_just_pressed.side_effect = None
        self.input_manager.is_action_just_released.side_effect = (
            lambda a: a == "select"
        )
        self.system.update(self.world, 0.1)
        _drain_and_execute(self.buf, self.world)

        self.assertIsNotNone(captured_event)
        self.assertEqual(captured_event.entity_ids, ())

    def test_placement_requested_event(self) -> None:
        """Clicking in placement mode fires a PlacementRequestedEvent."""
        self.input_service.start_placement("reimu", 100, "yukkuri")

        self.input_manager.get_mouse_position.return_value = (200, 200)
        self.yukkurrium.screen_to_world.return_value = (200, 200)

        captured_event = None

        def on_requested(e: PlacementRequestedEvent) -> None:
            nonlocal captured_event
            captured_event = e

        self.event_bus.subscribe(PlacementRequestedEvent, on_requested)

        self.input_manager.is_action_just_pressed.side_effect = (
            lambda a: a == "select"
        )
        self.system.update(self.world, 0.1)
        _drain_and_execute(self.buf, self.world)

        self.assertIsNotNone(captured_event)
        self.assertIsInstance(captured_event, PlacementRequestedEvent)
        self.assertEqual(captured_event.x, 200)
        self.assertEqual(captured_event.y, 200)
        self.assertEqual(captured_event.type_id, "reimu")
        self.assertFalse(self.input_service.is_placing)

    def test_placement_cancellation_on_right_click(self) -> None:
        """Right-clicking in placement mode cancels placement (via command)."""
        self.input_service.start_placement("reimu", 100, "yukkuri")

        self.input_manager.is_action_just_pressed.side_effect = (
            lambda a: a == "cancel_action"
        )
        self.system.update(self.world, 0.1)
        _drain_and_execute(self.buf, self.world)

        self.assertFalse(self.input_service.is_placing)


if __name__ == "__main__":
    unittest.main()
