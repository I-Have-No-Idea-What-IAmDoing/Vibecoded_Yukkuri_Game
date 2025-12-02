"""
Tests for Social System Logic Regression.
"""
import pytest
from unittest.mock import Mock, MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.game.yukkuri_components import YukkuriStats, RelationshipRegistry, EmotionalState, Skills, SkillState
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.types import EntityID

@pytest.fixture
def social_env():
    world = World()
    event_bus = EventBus()
    system = SocialSystem(event_bus)
    world.add_system(system)

    trait_service = Mock(spec=TraitService)
    # Mock default interaction to avoid failures
    trait_service.get_interaction.return_value = {"base_impact": 0.0}
    world.services.register(trait_service, TraitService)

    skill_service = Mock(spec=SkillService)
    world.services.register(skill_service, SkillService)

    return world, system, skill_service, trait_service

def test_fight_damage_and_xp(social_env):
    world, system, skill_service, trait_service = social_env

    # 1. Setup Entities
    attacker = world.create_entity()
    world.add_component(attacker, YukkuriStats(name="Attacker", type_id="t", health=100.0))
    world.add_component(attacker, Transform(x=0, y=0))
    world.add_component(attacker, RelationshipRegistry())
    world.add_component(attacker, Skills()) # Needed for XP check? System uses service directly.

    defender = world.create_entity()
    world.add_component(defender, YukkuriStats(name="Defender", type_id="t", health=100.0))
    world.add_component(defender, Transform(x=10, y=0))
    world.add_component(defender, RelationshipRegistry())

    # Mock interaction definition for Fight
    trait_service.get_interaction.side_effect = lambda t: {"base_impact": -10.0} if t == "Fight" else None

    # 2. Trigger Fight via Request
    req = InteractionRequest(target_id=EntityID(defender), action="Fight")
    world.add_component(attacker, req)

    # 3. Update System
    system.update(world, 0.1)

    # 4. Verify Damage (Hardcoded 5.0 in updated system)
    attacker_stats = world.get_component(attacker, YukkuriStats)
    defender_stats = world.get_component(defender, YukkuriStats)

    assert attacker_stats.health == 95.0 # 100 - 5
    assert defender_stats.health == 95.0 # 100 - 5

    # 5. Verify XP (Combat for Fight)
    skill_service.add_xp.assert_called_with(attacker, "combat", 10.0)

def test_dance_xp(social_env):
    world, system, skill_service, trait_service = social_env

    dancer = world.create_entity()
    world.add_component(dancer, YukkuriStats(name="Dancer", type_id="t"))
    world.add_component(dancer, Transform(x=0, y=0))
    world.add_component(dancer, RelationshipRegistry())

    partner = world.create_entity()
    world.add_component(partner, YukkuriStats(name="Partner", type_id="t"))
    world.add_component(partner, Transform(x=10, y=0))
    world.add_component(partner, RelationshipRegistry())

    trait_service.get_interaction.side_effect = lambda t: {"base_impact": 10.0} if t == "Dance" else None

    req = InteractionRequest(target_id=EntityID(partner), action="Dance")
    world.add_component(dancer, req)

    system.update(world, 0.1)

    # Verify XP (Athletics + Socialization)
    # Check calls
    calls = skill_service.add_xp.call_args_list
    # Should be called for athletics 5.0 and social 2.0
    assert any(c[0] == (dancer, "athletics", 5.0) for c in calls)
    assert any(c[0] == (dancer, "socialization", 2.0) for c in calls)

def test_talk_xp(social_env):
    world, system, skill_service, trait_service = social_env

    talker = world.create_entity()
    world.add_component(talker, YukkuriStats(name="Talker", type_id="t"))
    world.add_component(talker, Transform(x=0, y=0))
    world.add_component(talker, RelationshipRegistry())

    listener = world.create_entity()
    world.add_component(listener, YukkuriStats(name="Listener", type_id="t"))
    world.add_component(listener, Transform(x=10, y=0))
    world.add_component(listener, RelationshipRegistry())

    trait_service.get_interaction.side_effect = lambda t: {"base_impact": 5.0} if t == "Talk" else None

    req = InteractionRequest(target_id=EntityID(listener), action="Talk")
    world.add_component(talker, req)

    system.update(world, 0.1)

    skill_service.add_xp.assert_called_with(talker, "socialization", 5.0)
