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
from yukkuri_game.game.services import InputService
from yukkuri_game.engine.input_manager import InputManager


class TestUIEvents(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.yukkurrium = MagicMock()
        self.system = InputSystem(self.yukkurrium)

        # Mock EventBus
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        # Mock InputService
        self.input_service = InputService()
        self.world.services.register(self.input_service)

        # Mock InputManager
        self.input_manager = MagicMock(spec=InputManager)
        self.world.services.register(self.input_manager, InputManager)

        # Setup Yukkurrium mock default return
        self.yukkurrium.screen_to_world.return_value = (0, 0)

        # Setup InputManager defaults
        self.input_manager.get_mouse_position.return_value = (0, 0)
        self.input_manager.is_action_just_pressed.return_value = False
        self.input_manager.is_action_just_released.return_value = False
        self.input_manager.is_action_pressed.return_value = False

        # Mock pygame.display for update loop
        self.patcher = patch("yukkuri_game.game.input_system.pygame.display.get_surface")
        self.mock_get_surface = self.patcher.start()
        self.mock_surface = MagicMock()
        self.mock_surface.get_size.return_value = (800, 600)
        self.mock_get_surface.return_value = self.mock_surface

        # Run update once to initialize lazy dependencies
        self.system.update(self.world, 0.0)

    def tearDown(self):
        self.patcher.stop()

    @patch("pygame.key.get_pressed")
    def test_entity_selection_event(self, mock_get_pressed):
        # Mock shift key not pressed
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = False
        mock_get_pressed.return_value = mock_keys

        # Setup: Click at (100, 100) on an entity
        self.input_manager.get_mouse_position.return_value = (100, 100)
        self.yukkurrium.screen_to_world.return_value = (100, 100)

        # Create entity
        entity_id = self.world.create_entity()
        self.world.add_component(entity_id, Transform(x=100, y=100))
        self.world.add_component(entity_id, Selectable())

        # Setup Selection Capture
        captured_event = None

        def on_selected(e):
            nonlocal captured_event
            captured_event = e

        self.event_bus.subscribe(EntitySelectedEvent, on_selected)

        # Simulate Press "select"
        self.input_manager.is_action_just_pressed.side_effect = lambda a: a == "select"

        # Call Update (Press)
        self.system.update(self.world, 0.1)

        # Verify Drag Start
        self.assertIsNotNone(self.system.drag_start_pos)

        # Simulate Release "select"
        self.input_manager.is_action_just_pressed.return_value = False  # Reset press
        self.input_manager.is_action_just_pressed.side_effect = None

        self.input_manager.is_action_just_released.side_effect = lambda a: a == "select"

        # Call Update (Release)
        self.system.update(self.world, 0.1)

        self.assertIsNotNone(captured_event)
        self.assertIsInstance(captured_event, EntitySelectedEvent)
        self.assertIn(entity_id, captured_event.entity_ids)

    @patch("pygame.key.get_pressed")
    def test_entity_deselection_event(self, mock_get_pressed):
        # Mock shift key not pressed
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = False
        mock_get_pressed.return_value = mock_keys

        # Setup: Click far away (500, 500)
        self.input_manager.get_mouse_position.return_value = (500, 500)
        self.yukkurrium.screen_to_world.return_value = (500, 500)

        # Create entity at (100, 100)
        entity_id = self.world.create_entity()
        self.world.add_component(entity_id, Transform(x=100, y=100))
        self.world.add_component(
            entity_id, Selectable(selected=True)
        )  # Already selected

        captured_event = None

        def on_selected(e):
            nonlocal captured_event
            captured_event = e

        self.event_bus.subscribe(EntitySelectedEvent, on_selected)

        # Simulate Press "select"
        self.input_manager.is_action_just_pressed.side_effect = lambda a: a == "select"
        self.system.update(self.world, 0.1)

        # Simulate Release "select"
        self.input_manager.is_action_just_pressed.return_value = False
        self.input_manager.is_action_just_pressed.side_effect = None
        self.input_manager.is_action_just_released.side_effect = lambda a: a == "select"

        self.system.update(self.world, 0.1)

        self.assertIsNotNone(captured_event)
        self.assertEqual(captured_event.entity_ids, ())

    def test_placement_requested_event(self) -> None:
        # Start placement mode
        self.input_service.start_placement("reimu", 100, "yukkuri")

        # Setup: Click at (200, 200)
        self.input_manager.get_mouse_position.return_value = (200, 200)
        self.yukkurrium.screen_to_world.return_value = (200, 200)

        captured_event = None

        def on_requested(e):
            nonlocal captured_event
            captured_event = e

        self.event_bus.subscribe(PlacementRequestedEvent, on_requested)

        # Simulate Press "select"
        self.input_manager.is_action_just_pressed.side_effect = lambda a: a == "select"

        self.system.update(self.world, 0.1)

        self.assertIsNotNone(captured_event)
        self.assertIsInstance(captured_event, PlacementRequestedEvent)
        self.assertEqual(captured_event.x, 200)
        self.assertEqual(captured_event.y, 200)
        self.assertEqual(captured_event.type_id, "reimu")
        self.assertFalse(self.input_service.is_placing)

    def test_placement_cancellation_on_right_click(self) -> None:
        # Start placement mode
        self.input_service.start_placement("reimu", 100, "yukkuri")

        # Simulate "cancel_action"
        self.input_manager.is_action_just_pressed.side_effect = (
            lambda a: a == "cancel_action"
        )

        self.system.update(self.world, 0.1)

        self.assertFalse(self.input_service.is_placing)


if __name__ == "__main__":
    unittest.main()
