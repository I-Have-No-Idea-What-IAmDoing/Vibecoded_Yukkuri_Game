import pytest
from test_utils import make_configured_world
from unittest.mock import MagicMock, patch
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
    LogMessageEvent,
)


@pytest.fixture
def mock_world():
    return make_configured_world()


@pytest.fixture
def mock_factory(mock_world):
    factory = MagicMock(spec=EntityFactory)
    mock_world.services.register(factory, EntityFactory)
    return factory


@pytest.fixture
def mock_event_bus(mock_world):
    event_bus = mock_world.services.get(EventBus)
    # Mock publish for assertions in existing tests
    event_bus.publish = MagicMock()
    return event_bus


@pytest.fixture
def feedback_system(mock_world, mock_factory, mock_event_bus):
    sys = FeedbackSystem()
    mock_world.add_system(sys)
    return sys


class TestFeedbackSystem:
    def test_update_movement_and_lifetime(self, feedback_system, mock_world):
        # Setup an entity with FloatingText
        entity_id = mock_world.create_entity()
        transform = Transform(x=100, y=100)
        text_comp = FloatingText(
            text="Test",
            color=(255, 255, 255),
            lifetime=1.0,
            max_lifetime=1.0,
            velocity_y=-10.0,
            size=10,
        )
        mock_world.add_component(entity_id, transform)
        mock_world.add_component(entity_id, text_comp)

        # Update for 0.5 seconds
        feedback_system.update(mock_world, 0.5)

        # Check movement: y should decrease by 5 (velocity -10 * 0.5)
        assert transform.y == 95.0
        # Check lifetime: should be 0.5
        assert text_comp.lifetime == pytest.approx(0.5)
        # Should not be destroyed yet
        assert mock_world.entity_exists(entity_id)

        # Update for another 0.6 seconds (lifetime expires)
        feedback_system.update(mock_world, 0.6)

        assert text_comp.lifetime < 0
        assert not mock_world.entity_exists(entity_id)

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_entity_sold(
        self, mock_create_text, feedback_system, mock_factory, mock_event_bus
    ):
        event = EntitySoldEvent(entity_id=1, value=100, position=(50, 50))

        feedback_system.on_entity_sold(event)

        # Check floating text creation
        mock_create_text.assert_called()

        # Check log message
        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert isinstance(log_event, LogMessageEvent)
        assert "Sold entity for $100" in log_event.message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_growth(
        self,
        mock_create_text,
        feedback_system,
        mock_world,
        mock_factory,
        mock_event_bus,
    ):
        entity = mock_world.create_entity()
        # Mock stats component to get name
        stats = YukkuriStats(name="Reimu", type_id="reimu")
        mock_world.add_component(entity, stats)

        event = EntityGrewEvent(entity_id=entity, new_stage="Adult", position=(100, 100))
        feedback_system.on_growth(event)

        mock_create_text.assert_called()

        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert "Reimu grew into a Adult" in log_event.message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_death(
        self,
        mock_create_text,
        feedback_system,
        mock_world,
        mock_factory,
        mock_event_bus,
    ):
        entity = mock_world.create_entity()
        stats = YukkuriStats(name="Marisa", type_id="marisa")
        mock_world.add_component(entity, stats)

        event = EntityDiedEvent(entity_id=entity, position=(200, 200))
        feedback_system.on_death(event)

        mock_create_text.assert_called()

        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert "Marisa has died" in log_event.message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_trained(
        self,
        mock_create_text,
        feedback_system,
        mock_world,
        mock_factory,
        mock_event_bus,
    ):
        entity = mock_world.create_entity()
        stats = YukkuriStats(name="Alice", type_id="alice")
        mock_world.add_component(entity, stats)

        event = EntityTrainedEvent(entity_id=entity, position=(300, 300))
        feedback_system.on_trained(event)

        mock_create_text.assert_called()

        args, _ = mock_event_bus.publish.call_args
        log_event = args[0]
        assert "Alice trained successfully" in log_event.message
