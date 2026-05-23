"""
Tests for Social System Logic Regression.
"""

import pytest
from test_utils import make_configured_world
from unittest.mock import Mock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.game.components import InteractionRequest
from yukkuri_game.engine.components import Transform
from yukkuri_game.game.components import (
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


def test_destroyed_entity_relationship_cleanup(social_env):
    """
    Verify that when an entity is destroyed, other entities' relationship
    registries immediately prune any references to it.
    """
    world, _, _, _ = social_env
    social_system = world.services.get(SocialSystem)

    # 1. Setup Entities
    subject = world.create_entity()
    registry = RelationshipRegistry()
    world.add_component(subject, registry)

    other = world.create_entity()
    other_id = EntityID(other)

    # Populate relationships and biological links referencing 'other'
    from yukkuri_game.game.components import RelationshipData
    registry.relationships[other_id] = RelationshipData()
    registry.mate_id = other_id
    registry.biological_parents = [other_id]
    registry.biological_children = [other_id]

    # Verify they are present
    assert other_id in registry.relationships
    assert registry.mate_id == other_id
    assert registry.biological_parents == [other_id]
    assert registry.biological_children == [other_id]

    # 2. Destroy the 'other' entity
    world.destroy_entity(other)
    world.commands.apply_all()

    # 3. Trigger social system update to run cleanup
    social_system.update(world, 0.1)

    # 4. Verify all references to 'other' have been pruned!
    assert other_id not in registry.relationships
    assert registry.mate_id is None
    assert registry.biological_parents == []
    assert registry.biological_children == []


def test_destroyed_entity_perception_cleanup(social_env):
    """
    Verify that when an entity is destroyed, other entities' blackboard
    and AIState references immediately prune any references to it.
    """
    world, _, _, _ = social_env
    # Add PerceptionSystem to world
    from yukkuri_game.game.systems.perception_system import PerceptionSystem
    from yukkuri_game.game.components import Blackboard, AIState

    # Check if PerceptionSystem is already in world
    system = world.services.try_get(PerceptionSystem)
    if not system:
        system = PerceptionSystem()
        world.add_system(system)

    subject = world.create_entity()
    blackboard = Blackboard()
    ai_state = AIState()
    world.add_component(subject, blackboard)
    world.add_component(subject, ai_state)

    other = world.create_entity()
    other_id = EntityID(other)

    # Populate references
    blackboard.visible_targets[other_id] = None  # type: ignore
    blackboard.short_term_memory[other_id] = None  # type: ignore
    blackboard.closest_threat_id = other_id
    blackboard.closest_food_id = other_id
    ai_state.current_target_id = other_id
    ai_state.failed_targets.add(other_id)
    ai_state.visible_entities.add(other_id)

    # Destroy the other entity
    world.destroy_entity(other)
    world.commands.apply_all()

    # Verify everything has been immediately cleaned up in blackboard and ai_state!
    assert other_id not in blackboard.visible_targets
    assert other_id not in blackboard.short_term_memory
    assert blackboard.closest_threat_id is None
    assert blackboard.closest_food_id is None
    assert ai_state.current_target_id == EntityID(-1)
    assert other_id not in ai_state.failed_targets
    assert other_id not in ai_state.visible_entities
