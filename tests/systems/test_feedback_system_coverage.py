import pytest
from test_utils import make_configured_world
from unittest.mock import MagicMock, patch
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.feedback_system import FeedbackSystem
from yukkuri_game.engine.components import Transform, FloatingText
from yukkuri_game.game.components import YukkuriStats
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.game.events import (
    EntitySoldEvent,
    EntityGrewEvent,
    EntityTrainedEvent,
    EntityPunishedEvent,
    EntityDiedEvent,
    LogMessageEvent,
)


class TestFeedbackSystem:
    @pytest.fixture
    def mock_world(self):
        return make_configured_world()

    @pytest.fixture
    def system(self, mock_world):
        sys = FeedbackSystem()
        mock_world.add_system(sys)
        # Mock publish for easier assertions in existing tests
        sys.event_bus.publish = MagicMock()
        return sys

    def test_update_floating_text(self, system, mock_world):
        e1 = mock_world.create_entity()
        trans = Transform(x=0, y=0)
        text = FloatingText(
            text="Hi",
            velocity_y=-10.0,
            lifetime=0.2,
            color=(255, 255, 255),
            max_lifetime=0.2,
        )
        mock_world.add_component(e1, trans)
        mock_world.add_component(e1, text)

        # First update - text moves and lifetime decreases
        system.update(mock_world, 0.1)

        assert trans.y == -1.0  # 0 + (-10 * 0.1)
        assert text.lifetime == pytest.approx(0.1)
        assert mock_world.entity_exists(e1)

        # Second update - text expires
        system.update(mock_world, 0.2)
        assert text.lifetime < 0
        assert not mock_world.entity_exists(e1)

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_entity_sold(self, mock_create, system, mock_world):
        event = EntitySoldEvent(entity_id=1, value=100, position=(10, 20))
        system.on_entity_sold(event)

        mock_create.assert_called()
        # Verify log message
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert isinstance(args[0], LogMessageEvent)
        assert "Sold entity" in args[0].message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_growth(self, mock_create, system, mock_world):
        entity = mock_world.create_entity()
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.add_component(entity, stats)

        event = EntityGrewEvent(entity_id=entity, new_stage="Adult", position=(10, 20))
        system.on_growth(event)

        mock_create.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 grew into a Adult" in args[0].message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_death(self, mock_create, system, mock_world):
        entity = mock_world.create_entity()
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.add_component(entity, stats)

        event = EntityDiedEvent(entity_id=entity, position=(10, 20))
        system.on_death(event)

        mock_create.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 has died" in args[0].message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_trained(self, mock_create, system, mock_world):
        entity = mock_world.create_entity()
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.add_component(entity, stats)

        event = EntityTrainedEvent(entity_id=entity, position=(10, 20))
        system.on_trained(event)

        mock_create.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 trained successfully" in args[0].message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_on_punished(self, mock_create, system, mock_world):
        entity = mock_world.create_entity()
        stats = YukkuriStats(name="Y1", type_id="reimu")
        mock_world.add_component(entity, stats)

        event = EntityPunishedEvent(entity_id=entity, position=(10, 20))
        system.on_punished(event)

        mock_create.assert_called()
        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Y1 was punished" in args[0].message

    @patch("yukkuri_game.game.systems.feedback_system.create_floating_text")
    def test_handlers_missing_stats(self, mock_create, system, mock_world):
        # Test case where YukkuriStats is missing (e.g. invalid entity)
        # Just use a non-existent ID
        event = EntityDiedEvent(entity_id=999, position=(0, 0))
        system.on_death(event)

        assert system.event_bus.publish.called
        args, _ = system.event_bus.publish.call_args
        assert "Entity has died" in args[0].message
