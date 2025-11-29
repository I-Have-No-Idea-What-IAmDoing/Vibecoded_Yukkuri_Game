
import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, Personality
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.trait_service import TraitService

@pytest.fixture
def event_bus():
    return EventBus()

@pytest.fixture
def social_system(event_bus):
    return SocialSystem(event_bus)

@pytest.fixture
def mock_trait_service():
    return MagicMock(spec=TraitService)

def test_mood_update_low_health(event_bus, social_system, mock_trait_service):
    world = World()
    world.services.register(mock_trait_service, service_type=TraitService)

    entity = world.create_entity()
    stats = YukkuriStats(name="Victim", type_id="test", health=10.0, max_health=100.0)
    pers = Personality(mood="NEUTRAL", mood_score=0.0)

    world.add_component(entity, stats)
    world.add_component(entity, pers)

    social_system.update(world, 1.0)

    assert pers.mood == "SCARED"
    assert pers.mood_score == 80.0

def test_mood_update_high_stress(event_bus, social_system, mock_trait_service):
    world = World()
    world.services.register(mock_trait_service, service_type=TraitService)

    entity = world.create_entity()
    stats = YukkuriStats(name="Angry", type_id="test", stress=90.0)
    pers = Personality(mood="NEUTRAL", mood_score=0.0)

    world.add_component(entity, stats)
    world.add_component(entity, pers)

    social_system.update(world, 1.0)

    assert pers.mood == "FURIOUS"

def test_mood_decay(event_bus, social_system, mock_trait_service):
    world = World()
    world.services.register(mock_trait_service, service_type=TraitService)

    entity = world.create_entity()
    stats = YukkuriStats(name="Calm", type_id="test")
    # Strong mood but no underlying cause (stats are normal)
    pers = Personality(mood="HAPPY", mood_score=10.0)

    world.add_component(entity, stats)
    world.add_component(entity, pers)

    # Update for 1 second. Decay rate is 5.0/sec
    social_system.update(world, 1.0)

    # 10 - 5 = 5
    assert pers.mood == "HAPPY"
    assert pers.mood_score == 5.0

    # Update until decay
    social_system.update(world, 2.0)
    assert pers.mood == "NEUTRAL"
    assert pers.mood_score == 0.0
