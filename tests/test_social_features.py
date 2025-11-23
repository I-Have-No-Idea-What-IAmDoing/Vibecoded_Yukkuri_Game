import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import Personality, RelationshipRegistry, YukkuriStats
from yukkuri_game.game.systems.social_system import SocialSystem, FamilyManager
from yukkuri_game.game.services import TraitService, TimeService
from yukkuri_game.game.events import RelationshipChangedEvent
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.components import Transform

@pytest.fixture
def social_world(tmp_path):
    world = World()

    # Setup Services
    traits_dir = tmp_path / "data" / "traits"
    traits_dir.mkdir(parents=True)
    (traits_dir / "traits.toml").write_text("""
    [traits.GESU]
    name = "Gesu"
    """)

    interactions_dir = tmp_path / "data" / "ai"
    interactions_dir.mkdir(parents=True)
    (interactions_dir / "interactions.toml").write_text("""
    [interaction.Hit]
    base_impact = -20.0
    social_impact = { affinity = -10.0, fear = 5.0, trust = -10.0 }
    [interaction.Hit.modifiers]
    "trait:GESU" = { fear = 15.0 } # If victim is Gesu, fear +15

    [interaction.Greet]
    base_impact = 5.0
    social_impact = { affinity = 5.0 }
    can_recruit_family = true
    """)

    trait_service = TraitService(str(tmp_path / "data"))
    world.services.register(trait_service, TraitService)

    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    time_service = TimeService()
    world.services.register(time_service, TimeService)

    return world

def test_interaction_basics(social_world):
    sys = SocialSystem(social_world)

    # Create Entities
    e1 = social_world.create_entity() # Attacker
    social_world.add_component(e1, Personality())
    social_world.add_component(e1, RelationshipRegistry())
    social_world.add_component(e1, YukkuriStats("E1", "reimu"))
    social_world.add_component(e1, Transform(0,0))

    e2 = social_world.create_entity() # Victim
    social_world.add_component(e2, Personality())
    social_world.add_component(e2, RelationshipRegistry())
    social_world.add_component(e2, YukkuriStats("E2", "reimu"))
    social_world.add_component(e2, Transform(10,10))

    # Process Hit
    sys.process_interaction(e1, e2, "Hit")

    # Check E2's view of E1
    rels = social_world.get_component(e2, RelationshipRegistry)
    assert e1 in rels.relationships
    data = rels.relationships[e1]
    assert data.affinity == -10.0
    assert data.fear == 5.0

def test_trait_modifiers(social_world):
    sys = SocialSystem(social_world)

    e1 = social_world.create_entity()
    social_world.add_component(e1, Personality())
    social_world.add_component(e1, RelationshipRegistry())
    social_world.add_component(e1, YukkuriStats("E1", "reimu"))

    e2 = social_world.create_entity() # Victim (Gesu)
    pers = Personality(traits={"GESU"})
    social_world.add_component(e2, pers)
    social_world.add_component(e2, RelationshipRegistry())
    social_world.add_component(e2, YukkuriStats("E2", "reimu"))

    sys.process_interaction(e1, e2, "Hit")

    rels = social_world.get_component(e2, RelationshipRegistry)
    data = rels.relationships[e1]
    # Base fear 5.0 + Modifier 15.0 = 20.0
    assert data.fear == 20.0

def test_family_formation(social_world):
    sys = SocialSystem(social_world)

    e1 = social_world.create_entity()
    social_world.add_component(e1, Personality())
    r1 = RelationshipRegistry()
    social_world.add_component(e1, r1)
    social_world.add_component(e1, YukkuriStats("E1", "reimu"))

    e2 = social_world.create_entity()
    social_world.add_component(e2, Personality())
    r2 = RelationshipRegistry()
    social_world.add_component(e2, r2)
    social_world.add_component(e2, YukkuriStats("E2", "reimu"))

    # Manually set high affinity
    from yukkuri_game.game.yukkuri_components import RelationshipData
    r1.relationships[e2] = RelationshipData(affinity=60.0)
    r2.relationships[e1] = RelationshipData(affinity=60.0)

    sys.process_interaction(e1, e2, "Greet")

    assert r1.family_group_id is not None
    assert r1.family_group_id == r2.family_group_id

def test_visual_feedback_event(social_world):
    sys = SocialSystem(social_world)
    eb = social_world.services.get(EventBus)

    events_captured = []
    def on_change(e):
        events_captured.append(e)
    eb.subscribe(RelationshipChangedEvent, on_change)

    e1 = social_world.create_entity()
    social_world.add_component(e1, Personality())
    social_world.add_component(e1, RelationshipRegistry())
    social_world.add_component(e1, YukkuriStats("E1", "reimu"))
    social_world.add_component(e1, Transform(0,0)) # Position needed for event

    e2 = social_world.create_entity()
    social_world.add_component(e2, Personality())
    social_world.add_component(e2, RelationshipRegistry())
    social_world.add_component(e2, YukkuriStats("E2", "reimu"))
    social_world.add_component(e2, Transform(0,0)) # Position needed for event

    # Big Hit to trigger change
    sys.process_interaction(e1, e2, "Hit") # -10 affinity

    # Interaction needs to cause >10 change. Hit is -10.
    # 0 -> -10 is change of 10. condition is abs() > 10. So 10 is not > 10.
    # Need more impact or verify strict inequality.
    # Code: if abs(rel.affinity - old_affinity) > 10.0:
    # So -10 change is not enough. Let's hit twice or modify interaction.

    sys.process_interaction(e1, e2, "Hit") # Another -10 -> Total -20.
    # First hit: 0 -> -10. No event.
    # Second hit: -10 -> -20. Change is 10. No event.

    # Let's modify "Hit" impact to -20 in setup or hit multiple times.
    # Or just test logic:

    # Reset
    rels = social_world.get_component(e2, RelationshipRegistry)
    rels.relationships[e1].affinity = 0.0

    # Force a big change via internal method or stronger interaction
    # Let's use a custom interaction "Nuke"

    # Hack: modify loaded interaction
    sys.trait_service.interactions["interaction"]["Hit"]["social_impact"]["affinity"] = -20.0

    sys.process_interaction(e1, e2, "Hit")
    # 0 -> -20. Change 20. Should fire.

    assert len(events_captured) == 1
    assert events_captured[0].change_type == "negative"
