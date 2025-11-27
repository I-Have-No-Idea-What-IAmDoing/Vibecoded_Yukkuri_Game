import unittest
from unittest.mock import Mock, MagicMock
import pygame
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent, PlacementStartedEvent, GamePausedEvent
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.game.ui.hud import HUD
from yukkuri_game.engine.service_locator import ServiceLocator
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkurrium import Yukkurrium
from yukkuri_game.game.game_manager import GameManager
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.game.services import InputService

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.world.services.register(self.event_bus)

        # Mock dependencies
        self.yukkurrium = Mock(spec=Yukkurrium)
        self.world.services.register(self.yukkurrium)

        self.gm = Mock(spec=GameManager)
        self.world.services.register(self.gm, GameManager)

        self.factory = Mock(spec=EntityFactory)
        self.world.services.register(self.factory, EntityFactory)

        self.input_service = InputService()
        self.world.services.register(self.input_service, InputService)

        self.ui_manager = Mock()
        # Mock ui_manager methods that are called in HudLayout init
        self.ui_manager.get_theme.return_value.get_font.return_value = Mock()
        self.ui_manager.get_root_container.return_value = Mock()

    def test_input_system_publishes_selection_event(self):
        input_system = InputSystem(self.yukkurrium)
        # Trigger lazy init
        input_system.update(self.world, 0.0)

        # Mock subscriber
        mock_subscriber = Mock()
        self.event_bus.subscribe(EntitySelectedEvent, mock_subscriber)

        # Simulate click on entity
        # We need to setup world with an entity
        from yukkuri_game.game.components import Transform, Selectable
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(0, 0))
        self.world.add_component(entity, Selectable())

        # Mock screen_to_world to return 0,0
        self.yukkurrium.screen_to_world.return_value = (0, 0)

        # Simulate click event sequence (Down -> Up for drag logic)
        # We need to simulate mouse position via pygame.mouse.get_pos which we can't easily mock globally here without patching
        # But input_system.handle_event calls pygame.mouse.get_pos()

        with unittest.mock.patch('pygame.mouse.get_pos', return_value=(100, 100)), \
             unittest.mock.patch('pygame.key.get_pressed') as mock_get_pressed:

            # Mock key pressed to return dict with LSHIFT as False
            # pygame.key.get_pressed() returns a sequence of booleans indexed by K_ constants
            mock_keys = MagicMock()
            mock_keys.__getitem__.return_value = False # Default false
            mock_get_pressed.return_value = mock_keys

            # Mouse Down
            event_down = MagicMock(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 100))
            input_system.handle_event(event_down, self.world, 800, 600)

            # Mouse Up
            event_up = MagicMock(type=pygame.MOUSEBUTTONUP, button=1, pos=(100, 100))
            input_system.handle_event(event_up, self.world, 800, 600)

        # Check if event was published with correct entity
        mock_subscriber.assert_called_with(EntitySelectedEvent([entity]))

    def test_hud_subscribes_to_selection_event(self):
        with unittest.mock.patch('yukkuri_game.game.ui.hud.HudLayout') as MockLayout, \
             unittest.mock.patch('yukkuri_game.game.ui.hud.HudRenderer') as MockRenderer, \
             unittest.mock.patch('yukkuri_game.game.ui.hud.HudEvents') as MockEvents:

            # The factory mock needs an 'rm' attribute which has yukkuri_types and item_types
            rm_mock = Mock()
            rm_mock.yukkuri_types = {}
            rm_mock.item_types = {}
            self.factory.rm = rm_mock

            hud = HUD(self.ui_manager, self.world)

            # Publish event
            event = EntitySelectedEvent([123])
            self.event_bus.publish(event)

            self.assertEqual(hud.selected_entities, [123])

    def test_placement_event_flow(self):
        input_system = InputSystem(self.yukkurrium)
        input_system.update(self.world, 0.0) # Lazy init

        # Publish placement event
        event = PlacementStartedEvent("test_type", 100, "yukkuri")
        self.event_bus.publish(event)

        self.assertTrue(input_system.input_service.is_placing)
        self.assertEqual(input_system.input_service.place_type, "test_type")
        self.assertEqual(input_system.input_service.place_cost, 100)

if __name__ == '__main__':
    unittest.main()
