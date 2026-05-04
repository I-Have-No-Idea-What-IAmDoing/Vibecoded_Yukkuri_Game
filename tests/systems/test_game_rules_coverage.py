import pytest
from test_utils import make_configured_world
from unittest.mock import Mock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.systems.game_rules_system import GameRulesSystem
from yukkuri_game.game.events import (
    TrainEntityRequest,
    PunishEntityRequest,
    SellEntityRequest,
    EntitySoldEvent,
    EntityTrainedEvent,
    EntityPunishedEvent,
)
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, Needs, EmotionalState
from yukkuri_game.game.services import EconomyService


@pytest.fixture
def game_rules_env():
    world = make_configured_world()
    system = GameRulesSystem()
    world.add_system(system)

    economy = Mock(spec=EconomyService)
    economy.money = 1000
    world.services.register(economy, EconomyService)

    audio = Mock(spec=AudioManager)
    world.services.register(audio, AudioManager)

    event_bus = world.services.get(EventBus)
    return world, system, event_bus, economy, audio


def test_sell_yukkuri(game_rules_env):
    world, system, event_bus, economy, audio = game_rules_env

    entity = world.create_entity()
    world.add_component(entity, Transform(x=10, y=20))
    # Mock YukkuriStats with a predictable value calculation
    # Since calculate_value is a method on the component, we can let it run or mock it if needed.
    # Real component logic:
    stats = YukkuriStats(name="Marisa", type_id="marisa", badges=1, age=100)
    needs = Needs()
    world.add_component(entity, stats)
    world.add_component(entity, needs)
    world.add_component(entity, EmotionalState(happiness=50))

    # Capture events
    events = []
    event_bus.subscribe(EntitySoldEvent, lambda e: events.append(e))

    # Trigger Sell
    event_bus.publish(SellEntityRequest(entity))

    # Verify
    economy.add_money.assert_called_once()
    assert len(events) == 1
    assert events[0].entity_id == entity
    assert events[0].value > 0
    assert events[0].position == (10, 20)
    audio.play_sound.assert_called_with("sell")

    # Entity should be destroyed
    if world.entity_exists(entity):
        pytest.fail("Entity should be destroyed")


def test_train_yukkuri(game_rules_env):
    world, system, event_bus, economy, audio = game_rules_env

    entity = world.create_entity()
    world.add_component(entity, Transform(x=0, y=0))
    stats = YukkuriStats(name="Test", type_id="test", badges=0)
    world.add_component(entity, stats)
    emotion = EmotionalState(happiness=50)
    world.add_component(entity, emotion)

    events = []
    event_bus.subscribe(EntityTrainedEvent, lambda e: events.append(e))

    event_bus.publish(TrainEntityRequest(entity))

    assert stats.badges == 1
    assert emotion.happiness == 60.0
    assert len(events) == 1
    audio.play_sound.assert_called_with("train")


def test_punish_yukkuri(game_rules_env):
    world, system, event_bus, economy, audio = game_rules_env

    entity = world.create_entity()
    world.add_component(entity, Transform(x=0, y=0))
    stats = YukkuriStats(name="Test", type_id="test", discipline=0)
    needs = Needs(health=100)
    world.add_component(entity, stats)
    world.add_component(entity, needs)
    emotion = EmotionalState(happiness=50, stress=0)
    world.add_component(entity, emotion)

    events = []
    event_bus.subscribe(EntityPunishedEvent, lambda e: events.append(e))

    event_bus.publish(PunishEntityRequest(entity))

    assert needs.health == 90.0
    assert stats.discipline == 10.0
    assert emotion.happiness == 30.0
    assert emotion.stress == 20.0
    assert len(events) == 1
    audio.play_sound.assert_called_with("hit")


def test_action_on_missing_components(game_rules_env):
    """Ensure system handles entities missing components gracefully."""
    world, system, event_bus, _, _ = game_rules_env

    entity = world.create_entity()  # Empty entity

    # Should not crash
    event_bus.publish(SellEntityRequest(entity))
    event_bus.publish(TrainEntityRequest(entity))
    event_bus.publish(PunishEntityRequest(entity))

    assert world.entity_exists(entity)

