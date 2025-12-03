import pytest
from unittest.mock import Mock, MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.game.systems.hunger_system import HungerSystem
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats, EmotionalState, AIState, Personality
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.skill_service import SkillService

@pytest.fixture
def interaction_env():
    world = World()

    # Setup Services
    audio = Mock(spec=AudioManager)
    world.services.register(audio, AudioManager)

    trait_service = Mock(spec=TraitService)
    trait_service.calculate_overrides.return_value = {}
    world.services.register(trait_service, TraitService)

    skill_service = Mock(spec=SkillService)
    world.services.register(skill_service, SkillService)

    # Setup Systems
    # We need HungerSystem and SocialSystem registered as services or just systems added to world?
    # InteractionSystem looks them up via world.services.try_get(HungerSystem)

    hunger_system = HungerSystem()
    world.services.register(hunger_system, HungerSystem)

    social_system = Mock(spec=SocialSystem)
    world.services.register(social_system, SocialSystem)

    interaction_system = InteractionSystem()
    world.add_system(interaction_system)

    return world, interaction_system, audio, trait_service, hunger_system, social_system

def test_eat_item(interaction_env):
    world, system, audio, trait_service, hunger_system, social_system = interaction_env

    # Consumer
    consumer = world.create_entity()
    world.add_component(consumer, Transform(x=0, y=0))
    stats = YukkuriStats(name="Test", type_id="test", hunger=50)
    world.add_component(consumer, stats)
    world.add_component(consumer, EmotionalState(happiness=50))

    # Item
    item = world.create_entity()
    world.add_component(item, Transform(x=10, y=10))
    world.add_component(item, ItemStats(name="Item", type_id="item", cost=1, nutrition=20, fun=10))

    # Request
    req = InteractionRequest(target_id=item, consume=True)
    world.add_component(consumer, req)

    # Process
    system.update(world, 0.1)

    assert stats.hunger == 30 # 50 - 20
    assert world.get_component(consumer, EmotionalState).happiness == 60 # 50 + 10

    # Item consumed
    assert not world.entity_exists(item)
    assert not world.has_component(consumer, InteractionRequest)
    audio.play_sound.assert_called_with("eat")

def test_distance_check(interaction_env):
    world, system, audio, trait_service, hunger_system, social_system = interaction_env

    consumer = world.create_entity()
    world.add_component(consumer, Transform(x=0, y=0))
    world.add_component(consumer, YukkuriStats(name="Test", type_id="test"))

    item = world.create_entity()
    world.add_component(item, Transform(x=100, y=100)) # Far away
    world.add_component(item, ItemStats(name="Item", type_id="item", cost=1, nutrition=20))

    req = InteractionRequest(target_id=item, consume=True)
    world.add_component(consumer, req)

    # Note: InteractionSystem checks distance before dispatching for items too?
    # Let's check InteractionSystem.py logic.
    # _handle_interaction -> checks distance -> then dispatches.

    system.update(world, 0.1)

    # Should not consume (too far)
    assert world.entity_exists(item)

    # Request should still exist because it wasn't handled (distance check failed in InteractionSystem or HungerSystem)
    # Actually if InteractionSystem checks distance first and returns False, request is NOT removed.
    assert world.has_component(consumer, InteractionRequest)

def test_predation_not_allowed(interaction_env):
    world, system, audio, trait_service, hunger_system, social_system = interaction_env

    predator = world.create_entity()
    world.add_component(predator, Transform(x=0, y=0))
    predator_stats = YukkuriStats(name="Pred", type_id="pred", hunger=50)
    world.add_component(predator, predator_stats)
    world.add_component(predator, Personality(traits={"normal"}))

    prey = world.create_entity()
    world.add_component(prey, Transform(x=5, y=5))
    world.add_component(prey, YukkuriStats(name="Prey", type_id="prey"))

    # Default mock returns empty overrides, so can_eat_yukkuri is False

    req = InteractionRequest(target_id=prey, consume=True)
    world.add_component(predator, req)

    system.update(world, 0.1)

    # Should NOT eat
    assert world.entity_exists(prey)
    assert predator_stats.hunger == 50

def test_predation_allowed(interaction_env):
    world, system, audio, trait_service, hunger_system, social_system = interaction_env

    # Mock trait service to allow predation
    trait_service.calculate_overrides.return_value = {"can_eat_yukkuri": True}

    predator = world.create_entity()
    world.add_component(predator, Transform(x=0, y=0))
    predator_stats = YukkuriStats(name="Pred", type_id="pred", hunger=50)
    world.add_component(predator, predator_stats)
    world.add_component(predator, Personality(traits={"predator"}))

    prey = world.create_entity()
    world.add_component(prey, Transform(x=5, y=5))
    world.add_component(prey, YukkuriStats(name="Prey", type_id="prey"))

    req = InteractionRequest(target_id=prey, consume=True)
    world.add_component(predator, req)

    system.update(world, 0.1)

    # Should eat
    assert not world.entity_exists(prey)
    assert predator_stats.hunger == 0 # 50 - 50 = 0
    audio.play_sound.assert_called_with("eat")

def test_ai_target_reset(interaction_env):
    world, system, audio, trait_service, hunger_system, social_system = interaction_env

    consumer = world.create_entity()
    world.add_component(consumer, Transform(x=0, y=0))
    world.add_component(consumer, YukkuriStats(name="Test", type_id="test"))

    item = world.create_entity()
    world.add_component(item, Transform(x=0, y=0))
    world.add_component(item, ItemStats(name="Item", type_id="item", cost=1, nutrition=1))

    ai = AIState()
    ai.current_target_id = item
    world.add_component(consumer, ai)

    req = InteractionRequest(target_id=item, consume=True)
    world.add_component(consumer, req)

    # InteractionSystem should dispatch to HungerSystem which handles reset
    system.update(world, 0.1)

    assert ai.current_target_id == -1

def test_social_interaction_dispatch(interaction_env):
    world, system, audio, trait_service, hunger_system, social_system = interaction_env

    initiator = world.create_entity()
    world.add_component(initiator, Transform(x=0, y=0))
    world.add_component(initiator, YukkuriStats(name="Init", type_id="test"))

    target = world.create_entity()
    world.add_component(target, Transform(x=5, y=5))
    world.add_component(target, YukkuriStats(name="Target", type_id="test"))

    req = InteractionRequest(target_id=target, action="Greet")
    world.add_component(initiator, req)

    system.update(world, 0.1)

    # Should dispatch to SocialSystem
    social_system.process_interaction_request.assert_called_once()
    assert not world.has_component(initiator, InteractionRequest)
