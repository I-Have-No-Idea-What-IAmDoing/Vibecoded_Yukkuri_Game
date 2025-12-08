
import pytest
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.family_system import FamilySystem
from yukkuri_game.game.yukkuri_components import (
    YukkuriStats,
    RelationshipRegistry,
    AIState,
    EmotionalState,
    Needs,
    RelationshipData
)
from yukkuri_game.game.components import Transform
from yukkuri_game.game.systems.sector_system import SectorMap

class MockSectorMap:
    def __init__(self):
        self.entities = {}

    def add_entity(self, entity_id, x, y):
        self.entities[entity_id] = (x, y)

    def get_entities_in_range(self, x, y, range_type):
        # Determine range based on type
        radius = 150.0 if range_type == "visual" else 50.0

        results = []
        for eid, pos in self.entities.items():
            dist_sq = (pos[0] - x)**2 + (pos[1] - y)**2
            if dist_sq <= radius**2:
                results.append(eid)
        return results

@pytest.fixture
def world():
    w = World()
    return w

@pytest.fixture
def family_system():
    return FamilySystem()

def test_family_formation_no_family(world, family_system):
    """Test two entities with high affinity forming a new family."""

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry()
    s1 = YukkuriStats(name="Yukkuri1", type_id="TEST")
    world.add_component(e1, r1)
    world.add_component(e1, s1)

    # Entity 2
    e2 = world.create_entity()
    r2 = RelationshipRegistry()
    s2 = YukkuriStats(name="Yukkuri2", type_id="TEST")
    world.add_component(e2, r2)
    world.add_component(e2, s2)

    # Set high affinity
    r1.relationships[e2] = RelationshipData(affinity=90.0, trust=90.0)
    r2.relationships[e1] = RelationshipData(affinity=90.0, trust=90.0)

    # Run update
    family_system.update(world, 2.1)

    # Check if family formed
    assert r1.family_group_id is not None
    assert r2.family_group_id is not None
    assert r1.family_group_id == r2.family_group_id

def test_family_formation_join_existing(world, family_system):
    """Test an entity joining an existing family."""

    # Entity 1 (In a family)
    e1 = world.create_entity()
    r1 = RelationshipRegistry()
    r1.family_group_id = 12345
    s1 = YukkuriStats(name="Yukkuri1", type_id="TEST")
    world.add_component(e1, r1)
    world.add_component(e1, s1)

    # Entity 2 (No family)
    e2 = world.create_entity()
    r2 = RelationshipRegistry()
    s2 = YukkuriStats(name="Yukkuri2", type_id="TEST")
    world.add_component(e2, r2)
    world.add_component(e2, s2)

    # Set high affinity
    r1.relationships[e2] = RelationshipData(affinity=90.0, trust=90.0)

    family_system.update(world, 2.1)

    assert r2.family_group_id == 12345

def test_family_formation_reverse_join(world, family_system):
    """Test an entity joining an existing family (reverse check)."""

    # Entity 1 (No family)
    e1 = world.create_entity()
    r1 = RelationshipRegistry()
    s1 = YukkuriStats(name="Yukkuri1", type_id="TEST")
    world.add_component(e1, r1)
    world.add_component(e1, s1)

    # Entity 2 (In a family)
    e2 = world.create_entity()
    r2 = RelationshipRegistry()
    r2.family_group_id = 67890
    s2 = YukkuriStats(name="Yukkuri2", type_id="TEST")
    world.add_component(e2, r2)
    world.add_component(e2, s2)

    r1.relationships[e2] = RelationshipData(affinity=90.0, trust=90.0)

    family_system.update(world, 2.1)

    assert r1.family_group_id == 67890

def test_family_benefits_proximity(world, family_system):
    """Test happiness boost when family members are close."""

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry()
    r1.family_group_id = 100
    s1 = YukkuriStats(name="Y1", type_id="TEST")
    n1 = Needs()
    t1 = Transform(x=0, y=0)
    ai1 = AIState()
    em1 = EmotionalState(happiness=50.0, stress=50.0)

    world.add_component(e1, r1)
    world.add_component(e1, s1)
    world.add_component(e1, n1)
    world.add_component(e1, t1)
    world.add_component(e1, ai1)
    world.add_component(e1, em1)

    # Entity 2 (Close by)
    e2 = world.create_entity()
    r2 = RelationshipRegistry()
    r2.family_group_id = 100
    s2 = YukkuriStats(name="Y2", type_id="TEST")
    n2 = Needs()
    t2 = Transform(x=10, y=10)
    ai2 = AIState()
    em2 = EmotionalState(happiness=50.0, stress=50.0)

    world.add_component(e2, r2)
    world.add_component(e2, s2)
    world.add_component(e2, n2)
    world.add_component(e2, t2)
    world.add_component(e2, ai2)
    world.add_component(e2, em2)

    # Run update
    family_system.update(world, 2.1)

    # Check benefits applied (Happiness +0.5, Stress -0.5)
    assert em1.happiness == 50.5
    assert em1.stress == 49.5
    assert em2.happiness == 50.5
    assert em2.stress == 49.5

def test_family_benefits_too_far(world, family_system):
    """Test no benefits when family members are too far."""

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry(family_group_id=100)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="TEST"))
    world.add_component(e1, Needs())
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState())
    em1 = EmotionalState(happiness=50.0)
    world.add_component(e1, em1)

    # Entity 2 (Far away > 150)
    e2 = world.create_entity()
    r2 = RelationshipRegistry(family_group_id=100)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="TEST"))
    world.add_component(e2, Needs())
    world.add_component(e2, Transform(x=200, y=0))
    world.add_component(e2, AIState())
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    assert em1.happiness == 50.0
    assert em2.happiness == 50.0

def test_food_sharing(world, family_system):
    """Test food sharing behavior."""

    # Eater (Has food, eating)
    e1 = world.create_entity()
    world.add_component(e1, RelationshipRegistry(family_group_id=200))
    world.add_component(e1, YukkuriStats(name="Eater", type_id="TEST"))
    world.add_component(e1, Needs(hunger=0.0))
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState(current_action="Eat"))
    world.add_component(e1, EmotionalState())

    # Starver (Hungry, not eating)
    e2 = world.create_entity()
    world.add_component(e2, RelationshipRegistry(family_group_id=200))
    world.add_component(e2, YukkuriStats(name="Starver", type_id="TEST"))
    n2 = Needs(hunger=80.0)
    world.add_component(e2, n2)
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState(current_action="Idle"))
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    # Starver should get hunger reduction and happiness boost
    assert n2.hunger == 79.0 # 80 - 1
    # Happiness increases by 0.5 (proximity) + 0.5 (food sharing) = 1.0
    assert em2.happiness == 51.0

def test_nest_sharing(world, family_system):
    """Test nest sharing (sleep) behavior."""

    # Sleeper
    e1 = world.create_entity()
    world.add_component(e1, RelationshipRegistry(family_group_id=300))
    world.add_component(e1, YukkuriStats(name="Sleeper", type_id="TEST"))
    world.add_component(e1, Needs())
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState(current_action="Sleep"))
    world.add_component(e1, EmotionalState())

    # Partner
    e2 = world.create_entity()
    world.add_component(e2, RelationshipRegistry(family_group_id=300))
    world.add_component(e2, YukkuriStats(name="Partner", type_id="TEST"))
    n2 = Needs(energy=50.0)
    world.add_component(e2, n2)
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState(current_action="Idle"))
    em2 = EmotionalState(stress=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    # Partner benefits
    assert n2.energy == 50.5
    assert em2.stress == 48.5

def test_benefits_with_sector_map(world, family_system):
    """Test benefits logic when SectorMap is available (optimization path)."""

    sector_map = MockSectorMap()
    world.services.register(SectorMap, sector_map)

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry(family_group_id=400)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="TEST"))
    world.add_component(e1, Needs())
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState())
    em1 = EmotionalState(happiness=50.0)
    world.add_component(e1, em1)

    # Entity 2
    e2 = world.create_entity()
    r2 = RelationshipRegistry(family_group_id=400)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="TEST"))
    world.add_component(e2, Needs())
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState())
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    sector_map.add_entity(e1, 0, 0)
    sector_map.add_entity(e2, 10, 0)

    family_system.update(world, 2.1)

    # Benefits applied
    assert em1.happiness == 50.5
    assert em2.happiness == 50.5

def test_fallback_benefits_no_sector_map(world, family_system):
    """Test fallback logic when SectorMap is not present."""
    # Ensure SectorMap is NOT in services
    if world.services.try_get(SectorMap):
        world.services.unregister(SectorMap)

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry(family_group_id=500)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="TEST"))
    world.add_component(e1, Needs())
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState())
    em1 = EmotionalState(happiness=50.0)
    world.add_component(e1, em1)

    # Entity 2 (Close)
    e2 = world.create_entity()
    r2 = RelationshipRegistry(family_group_id=500)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="TEST"))
    world.add_component(e2, Needs())
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState())
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    assert em1.happiness == 50.5
    assert em2.happiness == 50.5

def test_fallback_benefits_different_families(world, family_system):
    """Test fallback logic ignores different families."""
    # Ensure SectorMap is NOT in services
    if world.services.try_get(SectorMap):
        world.services.unregister(SectorMap)

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry(family_group_id=600)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="TEST"))
    world.add_component(e1, Needs())
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState())
    em1 = EmotionalState(happiness=50.0)
    world.add_component(e1, em1)

    # Entity 2 (Different family)
    e2 = world.create_entity()
    r2 = RelationshipRegistry(family_group_id=601)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="TEST"))
    world.add_component(e2, Needs())
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState())
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    assert em1.happiness == 50.0
    assert em2.happiness == 50.0

def test_benefits_missing_components(world, family_system):
    """Test benefits logic handles missing components gracefully."""
    # Ensure SectorMap is NOT in services
    if world.services.try_get(SectorMap):
        world.services.unregister(SectorMap)

    # Entity 1 (Missing Needs)
    e1 = world.create_entity()
    r1 = RelationshipRegistry(family_group_id=700)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="TEST"))
    # world.add_component(e1, Needs()) # MISSING
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState())
    em1 = EmotionalState(happiness=50.0)
    world.add_component(e1, em1)

    # Entity 2
    e2 = world.create_entity()
    r2 = RelationshipRegistry(family_group_id=700)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="TEST"))
    world.add_component(e2, Needs())
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState())
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    assert em1.happiness == 50.0
    assert em2.happiness == 50.0

def test_benefits_no_emotional_state(world, family_system):
    """Test benefits logic when EmotionalState is missing (it's optional in _apply_benefit_pair)."""
    # Ensure SectorMap is NOT in services
    if world.services.try_get(SectorMap):
        world.services.unregister(SectorMap)

    # Entity 1
    e1 = world.create_entity()
    r1 = RelationshipRegistry(family_group_id=800)
    world.add_component(e1, r1)
    world.add_component(e1, YukkuriStats(name="Y1", type_id="TEST"))
    world.add_component(e1, Needs())
    world.add_component(e1, Transform(x=0, y=0))
    world.add_component(e1, AIState())
    # No EmotionalState

    # Entity 2
    e2 = world.create_entity()
    r2 = RelationshipRegistry(family_group_id=800)
    world.add_component(e2, r2)
    world.add_component(e2, YukkuriStats(name="Y2", type_id="TEST"))
    world.add_component(e2, Needs())
    world.add_component(e2, Transform(x=10, y=0))
    world.add_component(e2, AIState())
    em2 = EmotionalState(happiness=50.0)
    world.add_component(e2, em2)

    family_system.update(world, 2.1)

    # e1 has no emotion, so no crash.
    # e2 has emotion, should get boost.
    assert em2.happiness == 50.5
