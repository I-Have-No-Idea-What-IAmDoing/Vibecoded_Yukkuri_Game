import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.components import (
    RelationshipRegistry,
    YukkuriStats,
    RelationshipData,
    Personality,
    EmotionalState
)
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.components import InteractionRequest
from yukkuri_game.engine.components import Transform

@pytest.fixture
def world():
    w = World()
    # Mock services
    w.services.register(MagicMock(), TraitService)
    w.services.register(MagicMock(time_elapsed=100.0), TimeService)
    w.services.register(MagicMock(spec=EventBus), EventBus)
    return w

@pytest.fixture
def event_bus(world):
    return world.services.get(EventBus)

@pytest.fixture
def social_system(world):
    system = SocialSystem()
    world.add_system(system)
    return system

def test_social_cleanup(world, social_system):
    e1 = world.create_entity()
    e2 = world.create_entity()
    
    registry = RelationshipRegistry()
    registry.relationships[e2] = RelationshipData(
        last_update=10.0, # Very old (current time mocked as 100.0, but max age is 600... wait)
        # Max age is 600. Current 100. 100 - 10 = 90. Not old enough.
    )
    world.add_component(e1, registry)
    
    # Let's make it older than 600
    # Current time 1000
    time_service = world.services.get(TimeService)
    time_service.time_elapsed = 1000.0
    
    # 1000 - 10 = 990 > 600. Should be removed.
    
    social_system.update(world, 0.1)
    
    assert e2 not in registry.relationships

def test_interaction_request(world, social_system, event_bus):
    e1 = world.create_entity()
    e2 = world.create_entity()

    # Make sure targets exist
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e2, Transform(x=10, y=0))

    # Mock TraitService interaction data
    trait_service = world.services.get(TraitService)
    trait_service.get_interaction.return_value = {
        "base_impact": 10.0,
        "social_impact": {"affinity": 5.0, "trust": 2.0}
    }

    request = InteractionRequest(target_id=e2, action="Greet")
    social_system.process_interaction_request(world, e1, request)
    world.commands.apply_all()

    # Check if event was published
    assert event_bus.publish.called

    # Check if relationship was created/updated
    reg = world.try_get_component(e1, RelationshipRegistry)
    assert reg is not None
    assert e2 in reg.relationships
    assert reg.relationships[e2].trust > 0
    assert reg.relationships[e2].affinity > 0


def test_opinion_calculation(world, social_system):
    e1 = world.create_entity()
    e2 = world.create_entity()
    
    p1 = Personality() # Default axis
    p2 = Personality() # Default axis
    
    world.add_component(e1, p1)
    world.add_component(e2, p2)
    
    # Both default (50 everywhere). Diff is 0. Base compatibility should be 100.
    
    registry = RelationshipRegistry()
    rel_data = RelationshipData(affinity=0.0)
    registry.relationships[e2] = rel_data
    world.add_component(e1, registry)
    
    social_system.trait_service = world.services.get(TraitService) # Inject mock
    social_system._update_opinion(world, e1, e2, rel_data)
    
    assert rel_data.base_compatibility == 100.0
    assert rel_data.affinity == 100.0 # 100 base + 0 memory
