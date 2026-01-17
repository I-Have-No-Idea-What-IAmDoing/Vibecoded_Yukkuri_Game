import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.family_system import FamilySystem
from yukkuri_game.game.yukkuri_components import (
    RelationshipRegistry,
    YukkuriStats,
    RelationshipData,
    Needs,
    AIState,
    EmotionalState
)
from yukkuri_game.game.components import Transform
from yukkuri_game.game.systems.sector_system import SectorMap

@pytest.fixture
def world():
    return World()

@pytest.fixture
def family_system(world):
    system = FamilySystem()
    world.add_system(system)
    return system

def test_family_formation(world, family_system):
    # content...
    e1 = world.create_entity()
    e2 = world.create_entity()

    r1 = RelationshipRegistry()
    r1.relationships[e2] = RelationshipData(affinity=90.0, trust=90.0)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Yukkuri 1", type_id="test"))

    r2 = RelationshipRegistry()
    r2.relationships[e1] = RelationshipData(affinity=90.0, trust=90.0)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Yukkuri 2", type_id="test"))

    # Force check
    family_system.last_check = family_system.check_interval
    family_system.update(world, 0.1)

    assert r1.family_group_id is not None
    assert r1.family_group_id == r2.family_group_id

def test_family_benefits_proximity(world, family_system):
    # Setup two family members close to each other
    e1 = world.create_entity()
    e2 = world.create_entity()

    fid = 100
    r1 = RelationshipRegistry(family_group_id=fid)
    r2 = RelationshipRegistry(family_group_id=fid)
    
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="test"))
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, Needs())
    world.add_component(e1, AIState(current_action="Idle"))
    world.add_component(e1, EmotionalState(happiness=50.0))

    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="test"))
    world.add_component(e2, Transform(x=10, y=0)) # Close
    world.add_component(e2, Needs())
    world.add_component(e2, AIState(current_action="Idle"))
    world.add_component(e2, EmotionalState(happiness=50.0))

    # Mock SectorMap to avoid complex dependency
    # But FamilySystem uses try_get. If None, it uses fallback O(N^2).
    # Since we are testing logic, fallback is fine for unit test simplicity.

    family_system.last_check = family_system.check_interval
    family_system.update(world, 0.1)

    # Happiness should increase
    em1 = world.get_component(e1, EmotionalState)
    em2 = world.get_component(e2, EmotionalState)
    
    assert em1.happiness > 50.0
    assert em2.happiness > 50.0

def test_family_benefits_food_sharing(world, family_system):
    e1 = world.create_entity()
    e2 = world.create_entity()

    fid = 200
    
    # E1 is Eating
    world.add_component(e1, RelationshipRegistry(family_group_id=fid))
    world.add_component(e1, YukkuriStats(name="Y1", type_id="test"))
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, Needs(hunger=0.0))
    world.add_component(e1, AIState(current_action="Eat"))
    world.add_component(e1, EmotionalState())

    # E2 is Hungry
    world.add_component(e2, RelationshipRegistry(family_group_id=fid))
    world.add_component(e2, YukkuriStats(name="Y2", type_id="test"))
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, Needs(hunger=80.0)) # Hungry
    world.add_component(e2, AIState(current_action="Idle"))
    world.add_component(e2, EmotionalState())

    family_system.last_check = family_system.check_interval
    family_system.update(world, 0.1)

    needs2 = world.get_component(e2, Needs)
    assert needs2.hunger < 80.0 # Should have been reduced
