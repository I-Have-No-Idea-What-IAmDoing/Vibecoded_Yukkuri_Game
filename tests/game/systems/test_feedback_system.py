import pytest
from unittest.mock import MagicMock, call, patch
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.feedback_system import FeedbackSystem
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.game.components import Transform, FloatingText
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.game.events import (
    EntitySoldEvent,
    EntityGrewEvent,
    EntityTrainedEvent,
    EntityDiedEvent,
    LogMessageEvent
)

@pytest.fixture
def mock_world():
    world = MagicMock(spec=World)
    services = MagicMock()
    world.services = services
    return world

@pytest.fixture
def mock_factory(mock_world):
    factory = MagicMock(spec=EntityFactory)
    mock_world.services.get.side_effect = lambda service_type: factory if service_type == EntityFactory else mock_world.services.get_return_value
    return factory

@pytest.fixture
def mock_event_bus(mock_world):
    event_bus = MagicMock(spec=EventBus)
    # Update get side effect to handle multiple services
    def get_service(service_type):
        if service_type == EntityFactory:
            return mock_world.services.factory
        if service_type == EventBus:
            return event_bus
        return MagicMock()

    mock_world.services.get.side_effect = get_service
    return event_bus

@pytest.fixture
def feedback_system(mock_world, mock_factory, mock_event_bus):
    # Attach mocks to world for side_effect lambda to find
    mock_world.services.factory = mock_factory
    return FeedbackSystem(mock_world)

class TestFeedbackSystem:
    def test_update_movement_and_lifetime(self, feedback_system, mock_world):
        # Setup an entity with FloatingText
        entity_id = 1
        transform = Transform(x=100, y=100)
        text_comp = FloatingText(text="Test", color=(255, 255, 255), lifetime=1.0, max_lifetime=1.0, velocity_y=-10.0, size=10)

        # Mock get_components_tuple to handle different calls
        def get_components_side_effect(*args):
            if args == (YukkuriStats,):
                return [] # No Yukkuris for crying check
            if args == (Transform, FloatingText):
                return [(entity_id, (transform, text_comp))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_side_effect

        # Update for 0.5 seconds
        feedback_system.update(mock_world, 0.5)

        # Check movement: y should decrease by 5 (velocity -10 * 0.5)
        assert transform.y == 95.0
        # Check lifetime: should be 0.5
        assert text_comp.lifetime == 0.5
        # Should not be destroyed yet
        mock_world.destroy_entity.assert_not_called()

        # Update for another 0.6 seconds (lifetime expires)
        feedback_system.update(mock_world, 0.6)

        assert text_comp.lifetime < 0
        mock_world.destroy_entity.assert_called_with(entity_id)

    @patch('yukkuri_game.game.systems.feedback_system.create_floating_text')
    def test_on_entity_sold(self, mock_create_text, feedback_system, mock_factory, mock_event_bus):
        event = EntitySoldEvent(entity_id=1, value=100, position=(50, 50))

        feedback_system.on_entity_sold(event)

        # Check floating text creation
        mock_create_text.assert_called_with(feedback_system.world, 50, 20, "+$100", (255, 215, 0), size=24)

        # Check log message
        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert isinstance(log_event, LogMessageEvent)
        assert "Sold entity for $100" in log_event.message

    @patch('yukkuri_game.game.systems.feedback_system.create_floating_text')
    def test_on_growth(self, mock_create_text, feedback_system, mock_world, mock_factory, mock_event_bus):
        event = EntityGrewEvent(entity_id=1, new_stage="Adult", position=(100, 100))

        # Mock stats component to get name
        stats = YukkuriStats(name="Reimu", type_id="reimu")
        mock_world.get_component.return_value = stats

        feedback_system.on_growth(event)

        mock_create_text.assert_called_with(feedback_system.world, 100, 60, "Level Up!", (255, 255, 0), size=24)

        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert "Reimu grew into a Adult" in log_event.message

    @patch('yukkuri_game.game.systems.feedback_system.create_floating_text')
    def test_on_death(self, mock_create_text, feedback_system, mock_world, mock_factory, mock_event_bus):
        event = EntityDiedEvent(entity_id=1, position=(200, 200))

        stats = YukkuriStats(name="Marisa", type_id="marisa")
        mock_world.get_component.return_value = stats

        feedback_system.on_death(event)

        mock_create_text.assert_called_with(feedback_system.world, 200, 170, "Dead...", (128, 128, 128), size=20)

        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert "Marisa has died" in log_event.message

    @patch('yukkuri_game.game.systems.feedback_system.create_floating_text')
    def test_on_trained(self, mock_create_text, feedback_system, mock_world, mock_factory, mock_event_bus):
        event = EntityTrainedEvent(entity_id=1, position=(300, 300))

        stats = YukkuriStats(name="Alice", type_id="alice")
        mock_world.get_component.return_value = stats

        feedback_system.on_trained(event)

        mock_create_text.assert_called_with(feedback_system.world, 300, 270, "Trained!", (0, 255, 255), size=20)

        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert "Alice trained successfully" in log_event.message
