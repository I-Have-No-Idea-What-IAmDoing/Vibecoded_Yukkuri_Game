import unittest
from unittest.mock import MagicMock, patch
import pygame
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent, PlacementRequestedEvent, PlacementStartedEvent
from yukkuri_game.game.components import Transform, Selectable
from yukkuri_game.game.services import InputService

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

        # Need to run update once to initialize lazy dependencies
        self.system.update(self.world, 0.0)

    @patch('pygame.key.get_pressed')
    def test_entity_selection_event(self, mock_get_pressed):
        # Mock key pressed return (array of 0s, length 512 usually, or just accessible by index)
        # pygame.key.get_pressed() returns a ScancodeWrapper which behaves like a list
        # We can just return a mock that returns False for K_LSHIFT
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = False
        mock_get_pressed.return_value = mock_keys

        # Mock screen to world conversion
        self.yukkurrium.screen_to_world.return_value = (100, 100)

        # Create an entity at (100, 100)
        entity_id = self.world.create_entity()
        self.world.add_component(entity_id, Transform(x=100, y=100))
        self.world.add_component(entity_id, Selectable())

        # Mock a mouse click event
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (100, 100)})

        # Subscriber to capture event
        captured_event = None
        def on_selected(e):
            nonlocal captured_event
            captured_event = e
        self.event_bus.subscribe(EntitySelectedEvent, on_selected)

        # Handle event
        self.system.handle_event(event, self.world, 800, 600)

        # Need MOUSEBUTTONUP to trigger selection logic
        event_up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (100, 100)})
        self.system.handle_event(event_up, self.world, 800, 600)

        self.assertIsNotNone(captured_event)
        self.assertIsInstance(captured_event, EntitySelectedEvent)
        # Check if list contains the entity
        self.assertIn(entity_id, captured_event.entity_ids)

    @patch('pygame.key.get_pressed')
    def test_entity_deselection_event(self, mock_get_pressed):
        # Mock key pressed return (array of 0s, length 512 usually, or just accessible by index)
        # pygame.key.get_pressed() returns a ScancodeWrapper which behaves like a list
        # We can just return a mock that returns False for K_LSHIFT
        mock_keys = MagicMock()
        mock_keys.__getitem__.return_value = False
        mock_get_pressed.return_value = mock_keys

        # Ensure we are not clicking the entity
        # Entity is at 100, 100.
        # Click is at 500, 500.

        # Mock screen to world conversion
        self.yukkurrium.screen_to_world.return_value = (500, 500) # Click far away

        # Create an entity at (100, 100)
        entity_id = self.world.create_entity()
        self.world.add_component(entity_id, Transform(x=100, y=100))
        self.world.add_component(entity_id, Selectable())

        # Mock a mouse click event
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (500, 500)})

        captured_event = None
        def on_selected(e):
            nonlocal captured_event
            captured_event = e
        self.event_bus.subscribe(EntitySelectedEvent, on_selected)

        self.system.handle_event(event, self.world, 800, 600)

        # Need MOUSEBUTTONUP to trigger selection logic
        event_up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (500, 500)})
        self.system.handle_event(event_up, self.world, 800, 600)

        self.assertIsNotNone(captured_event)
        # Should be empty list for deselection
        self.assertEqual(captured_event.entity_ids, [])

    def test_placement_requested_event(self):
        # Start placement mode
        self.input_service.start_placement("reimu", 100, "yukkuri")

        # Mock screen to world
        self.yukkurrium.screen_to_world.return_value = (200, 200)

        # Mock mouse click
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (200, 200)})

        captured_event = None
        def on_requested(e):
            nonlocal captured_event
            captured_event = e
        self.event_bus.subscribe(PlacementRequestedEvent, on_requested)

        self.system.handle_event(event, self.world, 800, 600)

        self.assertIsNotNone(captured_event)
        self.assertIsInstance(captured_event, PlacementRequestedEvent)
        self.assertEqual(captured_event.x, 200)
        self.assertEqual(captured_event.y, 200)
        self.assertEqual(captured_event.type_id, "reimu")
        self.assertFalse(self.input_service.is_placing) # Should be cancelled after placement

    def test_placement_cancellation_on_right_click(self):
         # Start placement mode
        self.input_service.start_placement("reimu", 100, "yukkuri")

        # Mock screen to world for this test too, as handle_event calls it
        self.yukkurrium.screen_to_world.return_value = (0, 0)

        # Mock right click
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (0, 0)})

        self.system.handle_event(event, self.world, 800, 600)

        self.assertFalse(self.input_service.is_placing)

if __name__ == '__main__':
    unittest.main()
