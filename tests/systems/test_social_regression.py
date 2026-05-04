"""
Tests for Social System Logic Regression.
"""

import pytest
from test_utils import make_configured_world
from unittest.mock import Mock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.game.yukkuri_components import (
    YukkuriStats,
    Needs,
    RelationshipRegistry,
    Skills,
)
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.types import EntityID


@pytest.fixture
def social_env():
    world = make_configured_world()

    # We need both SocialSystem and InteractionSystem
    social_system = SocialSystem()
    world.services.register(social_system, SocialSystem)
    world.add_system(social_system)

    interaction_system = InteractionSystem()
    world.add_system(interaction_system)

    trait_service = Mock(spec=TraitService)
    # Mock default interaction to avoid failures
    trait_service.get_interaction.return_value = {"base_impact": 0.0}
    # Mock overrides for InteractionSystem
    trait_service.calculate_overrides.return_value = {}
    world.services.register(trait_service, TraitService)

    skill_service = Mock(spec=SkillService)
    world.services.register(skill_service, SkillService)

    return world, interaction_system, skill_service, trait_service


def test_fight_damage_and_xp(social_env):
    world, interaction_system, skill_service, trait_service = social_env

    # 1. Setup Entities
    attacker = world.create_entity()
    world.add_component(attacker, YukkuriStats(name="Attacker", type_id="t"))
    world.add_component(attacker, Needs(health=100.0, max_health=100.0))
    world.add_component(attacker, Transform(x=0, y=0))
    world.add_component(attacker, RelationshipRegistry())
    world.add_component(
        attacker, Skills()
    )  # Needed for XP check? System uses service directly.

    defender = world.create_entity()
    world.add_component(defender, YukkuriStats(name="Defender", type_id="t"))
    world.add_component(defender, Needs(health=100.0, max_health=100.0))
    world.add_component(defender, Transform(x=10, y=0))
    world.add_component(defender, RelationshipRegistry())

    # Mock interaction definition for Fight
    trait_service.get_interaction.side_effect = (
        lambda t: {
            "base_impact": -10.0,
            "physical_impact": {"health": -5.0},
            "skill_rewards": {"combat": 10.0},
        }
        if t == "Fight"
        else None
    )

    # 2. Trigger Fight via Request
    req = InteractionRequest(target_id=EntityID(defender), action="Fight")
    world.add_component(attacker, req)

    # 3. Update Interaction System (which calls SocialSystem logic)
    interaction_system.update(world, 0.1)

    # 4. Verify Damage (Hardcoded 5.0 in updated system)
    attacker_needs = world.get_component(attacker, Needs)
    defender_needs = world.get_component(defender, Needs)

    assert attacker_needs.health == 95.0  # 100 - 5
    assert defender_needs.health == 95.0  # 100 - 5

    # 5. Verify XP (Combat for Fight)
    skill_service.add_xp.assert_called_with(attacker, "combat", 10.0)


def test_dance_xp(social_env):
    world, interaction_system, skill_service, trait_service = social_env

    dancer = world.create_entity()
    world.add_component(dancer, YukkuriStats(name="Dancer", type_id="t"))
    world.add_component(dancer, Needs())
    world.add_component(dancer, Transform(x=0, y=0))
    world.add_component(dancer, RelationshipRegistry())

    partner = world.create_entity()
    world.add_component(partner, YukkuriStats(name="Partner", type_id="t"))
    world.add_component(partner, Needs())
    world.add_component(partner, Transform(x=10, y=0))
    world.add_component(partner, RelationshipRegistry())

    trait_service.get_interaction.side_effect = (
        lambda t: {
            "base_impact": 10.0,
            "skill_rewards": {"athletics": 5.0, "socialization": 2.0},
        }
        if t == "Dance"
        else None
    )

    req = InteractionRequest(target_id=EntityID(partner), action="Dance")
    world.add_component(dancer, req)

    interaction_system.update(world, 0.1)

    # Verify XP (Athletics + Socialization)
    # Check calls
    calls = skill_service.add_xp.call_args_list
    # Should be called for athletics 5.0 and social 2.0
    assert any(c[0] == (dancer, "athletics", 5.0) for c in calls)
    assert any(c[0] == (dancer, "socialization", 2.0) for c in calls)


def test_talk_xp(social_env):
    world, interaction_system, skill_service, trait_service = social_env

    talker = world.create_entity()
    world.add_component(talker, YukkuriStats(name="Talker", type_id="t"))
    world.add_component(talker, Needs())
    world.add_component(talker, Transform(x=0, y=0))
    world.add_component(talker, RelationshipRegistry())

    listener = world.create_entity()
    world.add_component(listener, YukkuriStats(name="Listener", type_id="t"))
    world.add_component(listener, Needs())
    world.add_component(listener, Transform(x=10, y=0))
    world.add_component(listener, RelationshipRegistry())

    trait_service.get_interaction.side_effect = (
        lambda t: {"base_impact": 5.0, "skill_rewards": {"socialization": 5.0}}
        if t == "Talk"
        else None
    )

    req = InteractionRequest(target_id=EntityID(listener), action="Talk")
    world.add_component(talker, req)

    interaction_system.update(world, 0.1)

    skill_service.add_xp.assert_called_with(talker, "socialization", 5.0)
