"""Regression test for trust clamping range.

Verifies that RelationshipData.trust can go negative after
hostile interactions, matching its documented range of -100 to 100.
"""

import pytest
from test_utils import make_configured_world
from unittest.mock import Mock

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.types import EntityID
from yukkuri_game.game.components import Transform
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.components import (
    Needs,
    Personality,
    RelationshipData,
    RelationshipRegistry,
    YukkuriStats,
)


@pytest.fixture
def trust_env():
    """Set up a minimal social environment for trust tests."""
    world = make_configured_world()

    trait_service = Mock(spec=TraitService)
    trait_service.get_trait.return_value = None
    world.services.register(trait_service, TraitService)

    social = SocialSystem()
    social.trait_service = trait_service
    world.add_system(social)

    actor = world.create_entity()
    world.add_component(actor, YukkuriStats(name="A", type_id="t"))
    world.add_component(actor, Needs())
    world.add_component(actor, Transform(x=0, y=0))
    world.add_component(actor, RelationshipRegistry())
    world.add_component(actor, Personality())

    target = world.create_entity()
    world.add_component(target, YukkuriStats(name="B", type_id="t"))
    world.add_component(target, Needs())
    world.add_component(target, Transform(x=10, y=0))
    world.add_component(target, RelationshipRegistry())
    world.add_component(target, Personality())

    return world, social, trait_service, actor, target


def test_hostile_interaction_produces_negative_trust(
    trust_env,
):
    """Trust must go below 0 after a hostile interaction."""
    world, social, trait_service, actor, target = trust_env

    trait_service.get_interaction.return_value = {
        "base_impact": -20.0,
        "social_impact": {"trust": -30.0},
    }

    social.register_interaction(world, actor, target, "Fight")

    registry = world.get_component(actor, RelationshipRegistry)
    rel = registry.relationships[EntityID(target)]
    assert rel.trust < 0, (
        f"Expected negative trust after hostile interaction, "
        f"got {rel.trust}"
    )


def test_trust_clamped_at_minus_100(trust_env):
    """Trust must not go below -100."""
    world, social, trait_service, actor, target = trust_env

    trait_service.get_interaction.return_value = {
        "base_impact": -50.0,
        "social_impact": {"trust": -200.0},
    }

    social.register_interaction(world, actor, target, "Fight")

    registry = world.get_component(actor, RelationshipRegistry)
    rel = registry.relationships[EntityID(target)]
    assert rel.trust == -100.0


def test_trust_clamped_at_plus_100(trust_env):
    """Trust must not exceed 100."""
    world, social, trait_service, actor, target = trust_env

    trait_service.get_interaction.return_value = {
        "base_impact": 50.0,
        "social_impact": {"trust": 200.0},
    }

    social.register_interaction(world, actor, target, "Talk")

    registry = world.get_component(actor, RelationshipRegistry)
    rel = registry.relationships[EntityID(target)]
    assert rel.trust == 100.0
