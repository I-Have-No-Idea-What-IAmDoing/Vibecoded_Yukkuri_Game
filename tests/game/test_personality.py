import pytest
import sys
import os
from unittest.mock import MagicMock

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.yukkuri_components import Personality, RelationshipRegistry, RelationshipData, YukkuriStats, AIState
from yukkuri_game.game.ai.utility import UtilityAIEngine, Action, Consideration
from yukkuri_game.game.ai.utility_selector import UtilitySelector
from yukkuri_game.game.systems.social_system import SocialSystem

# Mock ResourceManager
class MockResourceManager:
    def __init__(self):
        self.yukkuri_types = {
            "reimu": {
                "image": "reimu.png",
                "max_health": 100
            }
        }
        self.ai_actions = {
            "Eat": {
                "weight": 1.0,
                "considerations": [
                    {
                        "name": "HungerCheck",
                        "input": "hunger",
                        "curve": "linear",
                        "params": {"m": 1.0}
                    }
                ]
            }
        }

def test_trait_service_loading():
    # This assumes data/traits/traits.toml exists as created
    service = TraitService()
    assert "GESU" in service.traits
    assert "NICE" in service.traits

    gesu = service.get_trait("GESU")
    assert gesu["name"] == "Gesu"

    assert "Hit" in service.interactions

def test_utility_engine_overrides():
    rm = MockResourceManager()
    engine = UtilityAIEngine(rm)

    context = {"hunger": 50.0} # Normalized to 0.5

    # Normal Score: linear m=1.0 -> 0.5
    action_name = engine.select_action(context)
    assert action_name == "Eat"

    # Test Override
    # Let's say we have a personality that overrides HungerCheck to be 0
    # We mock the trait service and personality

    mock_trait_service = MagicMock()
    mock_trait_service.get_trait.return_value = {
        "ai_modifiers": {
            "HungerCheck": {"curve": "linear", "params": {"m": 0.0}}
        }
    }

    personality = Personality(traits={"ANOREXIC"}) # Fake trait

    # With override, score should be 0 (m=0 * 0.5 = 0)
    # Since "Eat" becomes 0, and "Idle" is fallback (implied 0 in this test setup?)
    # Wait, engine.select_action returns best. If Eat is 0, it might still return it if it's the only one
    # and default best_score is 0. But idle isn't in mock actions.
    # Engine defaults best_action="Idle".

    action_name = engine.select_action(context, personality, mock_trait_service)
    assert action_name == "Idle"

def test_social_system():
    world = World()
    ts = TraitService()
    world.services.register(ts) # Fix registration
    event_bus = EventBus()

    sys = SocialSystem(event_bus)
    world.add_system(sys) # Needed to inject ecs_world

    p1 = world.create_entity()
    world.add_component(p1, RelationshipRegistry())
    world.add_component(p1, Personality(traits={"NICE"})) # Nice helps?
    from yukkuri_game.game.components import Transform
    world.add_component(p1, Transform(x=0, y=0)) # Needed for visual feedback

    p2 = world.create_entity()

    # Test Hit
    sys.register_interaction(world, p2, p1, "Hit")
    # p2 hits p1. p1 is the subject (target).

    reg = world.get_component(p1, RelationshipRegistry)
    assert p2 in reg.relationships
    rel = reg.relationships[p2]

    # Hit: affinity -10.
    # We assert affinity drops
    assert rel.affinity < 0

    # We verify fear/trust are NOT checked because they are removed
