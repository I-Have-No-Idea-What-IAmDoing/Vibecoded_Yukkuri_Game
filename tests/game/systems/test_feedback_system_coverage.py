import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.feedback_system import FeedbackSystem
from yukkuri_game.game.components import Transform, FloatingText
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.game.events import (
    EntitySoldEvent,
    EntityGrewEvent,
    EntityTrainedEvent,
    EntityPunishedEvent,
    EntityDiedEvent,
    LogMessageEvent
)

class TestFeedbackSystem:
    @pytest.fixture
    def mock_world(self):
        world = MagicMock(spec=World)
        factory = MagicMock(spec=EntityFactory)
        event_bus = MagicMock(spec=EventBus)

        # services is an attribute, need to mock it as well
        services = MagicMock()
        world.services = services

        def get_service(t):
            if t == EntityFactory: return factory
            if t == EventBus: return event_bus
            return None

        services.get.side_effect = get_service
        return world

    @pytest.fixture
    def system(self, mock_world):
        return FeedbackSystem(mock_world)

    def test_update_floating_text(self, system, mock_world):
        e1 = 1
        trans = Transform(x=0, y=0)
        text = FloatingText(text="Hi", velocity_y=-10.0, lifetime=0.2, color=(255, 255, 255), max_lifetime=0.2)

        # Mock get_components_tuple
        def get_components_side_effect(*args):
            if args == (YukkuriStats,):
                return []
            if args == (Transform, FloatingText):
                return [(e1, (trans, text))]
            return []

        mock_world.get_components_tuple.side_effect = get_components_side_effect

        # First update - text moves and lifetime decreases
        system.update(mock_world, 0.1)

        assert trans.y == -1.0 # 0 + (-10 * 0.1)
        assert text.lifetime == 0.1
        mock_world.destroy_entity.assert_not_called()

        # Second update - text expires
        system.update(mock_world, 0.2)
        assert text.lifetime < 0
        mock_world.destroy_entity.assert_called_with(e1)

    def test_on_entity_sold(self, system, mock_world):
        event = EntitySoldEvent(entity_id=1, value=100, position=(10, 20))
        system.on_entity_sold(event)

        system.factory.create_floating_text.assert_called_with(10, -10, "+$100", (255, 215, 0), size=24)

        # Verify log message
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert isinstance(args[0], LogMessageEvent)
        assert "Sold entity" in args[0].message

    def test_on_growth(self, system, mock_world):
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.get_component.return_value = stats

        event = EntityGrewEvent(entity_id=1, new_stage="Adult", position=(10, 20))
        system.on_growth(event)

        system.factory.create_floating_text.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 grew into a Adult" in args[0].message

    def test_on_death(self, system, mock_world):
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.get_component.return_value = stats

        event = EntityDiedEvent(entity_id=1, position=(10, 20))
        system.on_death(event)

        system.factory.create_floating_text.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 has died" in args[0].message

    def test_on_trained(self, system, mock_world):
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.get_component.return_value = stats

        event = EntityTrainedEvent(entity_id=1, position=(10, 20))
        system.on_trained(event)

        system.factory.create_floating_text.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 trained successfully" in args[0].message

    def test_on_punished(self, system, mock_world):
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.get_component.return_value = stats

        event = EntityPunishedEvent(entity_id=1, position=(10, 20))
        system.on_punished(event)

        system.factory.create_floating_text.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 was punished" in args[0].message

    def test_handlers_missing_stats(self, system, mock_world):
        # Test case where YukkuriStats is missing (e.g. invalid entity)
        mock_world.get_component.return_value = None

        event = EntityDiedEvent(entity_id=999, position=(0,0))
        system.on_death(event)

        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Entity has died" in args[0].message
