import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.components import Transform, Selectable
from yukkuri_game.game.services import InputService

class TestInputSystem:
    @pytest.fixture
    def input_system(self):
        yukkurrium = MagicMock()
        # Mock screen_to_world to return simple mapping
        yukkurrium.screen_to_world.side_effect = lambda mx, my, sw, sh: (float(mx), float(my))
        return InputSystem(yukkurrium)

    @pytest.fixture
    def world(self):
        world = MagicMock(spec=World)
        input_service = MagicMock(spec=InputService)
        event_bus = MagicMock(spec=EventBus)

        # Mock services
        services = MagicMock()
        # Configure side_effect for get to return appropriate mock
        def get_service(service_type):
            if service_type == InputService:
                return input_service
            if service_type == EventBus:
                return event_bus
            return MagicMock()

        services.get.side_effect = get_service
        services.try_get.return_value = None

        world.services = services
        return world

    def test_check_hover_finds_entity(self, input_system, world):
        # Setup entities
        # ent1 at 100, 100
        ent1 = 1
        t1 = Transform(100, 100)

        # ent2 at 200, 200
        ent2 = 2
        t2 = Transform(200, 200)

        # Mock get_entities_with to return list of IDs (as implied by current codebase usage)
        # But robust implementation handles tuples too. Let's test robustness.
        world.get_entities_with.return_value = [ent1, ent2]

        def get_component_side_effect(ent, comp_type):
            if comp_type == Transform:
                if ent == ent1: return t1
                if ent == ent2: return t2
            return None

        world.get_component.side_effect = get_component_side_effect

        # Initialize dependencies
        input_system.update(world, 0.1)

        # Check hover near ent1
        input_system._check_hover(world, 105, 105, 105, 105)
        assert input_system.input_service.hovered_entity_id == ent1

        # Check hover near ent2
        input_system._check_hover(world, 205, 205, 205, 205)
        assert input_system.input_service.hovered_entity_id == ent2

        # Check hover no entity
        input_system._check_hover(world, 0, 0, 0, 0)
        assert input_system.input_service.hovered_entity_id == -1

    def test_check_hover_robustness_tuples(self, input_system, world):
        # Test if get_entities_with returns tuples (esper style)
        ent1 = 1
        t1 = Transform(100, 100)
        s1 = Selectable()

        world.get_entities_with.return_value = [(ent1, t1, s1)]

        def get_component_side_effect(ent, comp_type):
            if comp_type == Transform:
                if ent == ent1: return t1
            return None
        world.get_component.side_effect = get_component_side_effect

        input_system.update(world, 0.1)

        input_system._check_hover(world, 105, 105, 105, 105)
        assert input_system.input_service.hovered_entity_id == ent1
