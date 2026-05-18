from unittest.mock import MagicMock
from test_utils import make_configured_world
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.components import (
    Personality,
    RelationshipRegistry,
)
from yukkuri_game.game.ai.utility import UtilityAIEngine
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.engine.data_models import TraitDefinition


# Mock ResourceManager
class MockResourceManager:
    def __init__(self):
        self.yukkuri_types = {"reimu": {"image": "reimu.png", "max_health": 100}}
        self.ai_actions = {
            "Eat": {
                "weight": 1.0,
                "considerations": [
                    {
                        "name": "HungerCheck",
                        "input": "hunger",
                        "curve": "linear",
                        "params": {"m": 1.0},
                    }
                ],
            }
        }


def test_trait_service_loading():
    # Fix: Need world and resource manager for TraitService
    from yukkuri_game.engine.resource_manager import ResourceManager

    world = make_configured_world()
    rm = MagicMock(spec=ResourceManager)
    # TraitService loads traits as TraitDefinition objects
    t1 = TraitDefinition(name="Gesu", description="Gesu trait")
    t2 = TraitDefinition(name="Nice", description="Nice trait")
    rm.traits = {"GESU": t1, "NICE": t2}

    # Interactions are InteractionDefinition (or dicts as per current codebase flexibility)
    rm.interactions = {
        "Hit": {"base_impact": -10}
    }  # Assuming dict for simplicity or mock struct
    world.services.register(rm, ResourceManager)

    service = TraitService(world)
    assert "GESU" in service.traits
    assert "NICE" in service.traits

    gesu = service.get_trait("GESU")
    # Updated: Access attributes, not dict keys
    assert gesu.name == "Gesu"

    assert "Hit" in service.interactions


def test_utility_engine_overrides():
    rm = MockResourceManager()
    engine = UtilityAIEngine(rm)

    context = {"hunger": 50.0}  # Normalized to 0.5

    # Normal Score: linear m=1.0 -> 0.5
    action_name = engine.select_action(context)
    assert action_name == "Eat"

    # Test Override
    # Let's say we have a personality that overrides HungerCheck to be 0
    # We mock the trait service and personality

    mock_trait_service = MagicMock()
    # Return TraitDefinition object
    trait_def = TraitDefinition(
        name="Anorexic",
        description="Fake trait",
        ai_modifiers={"HungerCheck": {"curve": "linear", "params": {"m": 0.0}}},
    )

    mock_trait_service.get_trait.return_value = trait_def

    personality = Personality(traits={"ANOREXIC"})  # Fake trait

    # With override, score should be 0 (m=0 * 0.5 = 0)
    # Since "Eat" becomes 0, and "Idle" is fallback (implied 0 in this test setup?)
    # Wait, engine.select_action returns best. If Eat is 0, it might still return it if it's the only one
    # and default best_score is 0. But idle isn't in mock actions.
    # Engine defaults best_action="Idle".

    action_name = engine.select_action(context, personality, mock_trait_service)
    assert action_name == "Idle"


def test_social_system():
    world = make_configured_world()

    # Mock TraitService
    ts = MagicMock(spec=TraitService)
    # We are using dicts or structs?
    # TraitService loads structs, but mocks might be dicts unless convert
    # SocialSystem uses _get_attr helper, so dict is fine.

    # Mock Interaction: Hit
    hit_data = {"base_impact": -10.0, "social_impact": {"affinity": -10.0, "fear": 5.0}}

    ts.get_interaction.side_effect = lambda name: hit_data if name == "Hit" else None

    world.services.register(ts, TraitService)

    sys = SocialSystem()
    world.add_system(sys)  # Needed to inject ecs_world

    p1 = world.create_entity()
    world.add_component(p1, RelationshipRegistry())
    world.add_component(p1, Personality(traits={"NICE"}))  # Nice helps?
    from yukkuri_game.engine.components import Transform

    world.add_component(p1, Transform(x=0, y=0))  # Needed for visual feedback

    p2 = world.create_entity()

    # Test Hit
    sys.register_interaction(world, p2, p1, "Hit")
    # p2 hits p1. p1 is the subject (target).

    reg = world.get_component(p1, RelationshipRegistry)
    assert p2 in reg.relationships
    rel = reg.relationships[p2]

    # Hit: affinity -10.
    # If p1 is NICE? NO explicit modifier for NICE receiving a Hit in our data,
    # but "WEAK" and "PROUD" have modifiers.

    assert rel.affinity < 0
    assert rel.fear > 0
