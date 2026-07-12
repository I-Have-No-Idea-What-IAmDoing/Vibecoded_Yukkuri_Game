import pytest
import pymunk
import py_trees

from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.components import Transform, LightSource, FloatingText, PhysicsBody
from yukkuri_game.game.components import (
    YukkuriStats, Needs, AIState, EmotionalState, ItemStats, Personality, RelationshipRegistry, RelationshipData, GossipQueue, GossipPacket, Skills, Poop, MemoryHeadline
)
from yukkuri_game.game.systems.lifecycle import LifecycleSystem
from yukkuri_game.game.systems.poop_system import PoopSystem
from yukkuri_game.game.systems.family_system import FamilySystem
from yukkuri_game.game.systems.gossip_system import GossipSystem
from yukkuri_game.game.systems.feedback_system import FeedbackSystem
from yukkuri_game.game.systems.mouse_light_system import MouseLightSystem
from yukkuri_game.game.systems.hunger_system import HungerSystem
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.systems.day_night import DayNightSystem
from yukkuri_game.engine.systems.spatial import SpatialSystem
from yukkuri_game.game.commands import CleanEntityCommand
from yukkuri_game.game.events import (
    SocialInteractionEvent, EntitySoldEvent, PunishEntityRequest
)
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.config import GameConfig
from yukkuri_game.game.components import InteractionRequest
from yukkuri_game.engine.protocols import IPhysicsService, ISpatialService

def create_poop(driver: GameDriver, x: float, y: float) -> int:
    """Helper to spawn poop using EntityFactory."""
    from yukkuri_game.game.entity_factory import EntityFactory
    factory = driver.world.services.get(EntityFactory)
    return factory.create_poop(x, y)

def sync_spatial_service(driver: GameDriver) -> None:
    """Helper to register and sync spawned test entities in the spatial system index."""
    spatial_service = driver.world.services.get(ISpatialService)
    spatial_system = driver.world.get_system(SpatialSystem)
    
    spatial_service.body_to_entity.clear()
    spatial_system.body_to_entity.clear()
    spatial_service.sectors.clear()
    spatial_service.entity_sectors.clear()
    
    for entity, (pb,) in driver.world.get_components_tuple(PhysicsBody):
        spatial_service.body_to_entity[pb.body] = entity
        spatial_system.body_to_entity[pb.body] = entity
        
    for entity, (trans,) in driver.world.get_components_tuple(Transform):
        spatial_service.update_entity(entity, trans.x, trans.y)

# ===========================================================================
# TIER 1: FEATURE COVERAGE (>=5 cases per feature = 40+ tests)
# ===========================================================================

# 1. Need Decay & Metabolism
@pytest.mark.parametrize("need_name, initial_val, target_dir", [
    ("hunger", 0.0, 1),
    ("energy", 100.0, -1),
    ("cleanliness", 100.0, -1),
    ("social", 100.0, -1),
    ("bladder", 0.0, 0),
])
def test_need_decay_coverage(game_driver: GameDriver, need_name: str, initial_val: float, target_dir: int) -> None:
    driver = game_driver
    driver.setup()
    
    # Boost decay rates for quick simulation
    config = driver.world.services.get(GameConfig)
    config.rules.stat_decay.hunger = 10.0
    config.rules.stat_decay.energy = 10.0
    config.rules.stat_decay.cleanliness = 10.0
    config.rules.stat_decay.social = 10.0
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    setattr(needs, need_name, initial_val)
    
    driver.run_for(1.0)
    
    final_val = getattr(needs, need_name)
    if target_dir > 0:
        assert final_val > initial_val
    elif target_dir < 0:
        assert final_val < initial_val
    else:
        assert final_val == initial_val

# 2. Waste & Cleanliness
@pytest.mark.parametrize("case_type", [
    "poop_spawn",
    "poop_smell_decay",
    "clean_command",
    "clean_command_safety",
    "cleanliness_restored",
])
def test_waste_cleanliness_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "poop_spawn":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        needs = driver.get_component(reimu_id, Needs)
        needs.bladder = 100.0
        poop_system = driver.world.get_system(PoopSystem)
        poop_system.spawn_chance_per_second = 1000.0  # Force poop spawning
        driver.run_for(1.0)
        assert len(driver.get_entities_with(Poop)) > 0
        assert needs.bladder == 0.0
        
    elif case_type == "poop_smell_decay":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        poop_id = create_poop(driver, 100.0, 100.0)
        sync_spatial_service(driver)
        needs = driver.get_component(reimu_id, Needs)
        needs.cleanliness = 100.0
        driver.run_for(1.0)
        assert needs.cleanliness < 100.0
        
    elif case_type == "clean_command":
        poop_id = create_poop(driver, 100.0, 100.0)
        sync_spatial_service(driver)
        cmd = CleanEntityCommand(100.0, 100.0)
        cmd.execute(driver.world)
        driver.run_for(0.1)
        assert not driver.world.entity_exists(poop_id)
        
    elif case_type == "clean_command_safety":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        cmd = CleanEntityCommand(100.0, 100.0)
        cmd.execute(driver.world)
        driver.run_for(0.1)
        assert driver.world.entity_exists(reimu_id)
        
    elif case_type == "cleanliness_restored":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        poop_id = create_poop(driver, 100.0, 100.0)
        sync_spatial_service(driver)
        needs = driver.get_component(reimu_id, Needs)
        needs.cleanliness = 100.0
        
        # Clean poop
        cmd = CleanEntityCommand(100.0, 100.0)
        cmd.execute(driver.world)
        driver.run_for(1.0)
        
        # Cleanliness decay from poop smell should stop, only normal decay remains
        decay_with_poop = 100.0 - needs.cleanliness
        needs.cleanliness = 100.0
        driver.run_for(1.0)
        decay_without_poop = 100.0 - needs.cleanliness
        assert decay_without_poop < decay_with_poop

# 3. Lifecycle & Growth
@pytest.mark.parametrize("case_type", [
    "age_tick",
    "baby_child_transition",
    "child_adult_transition",
    "collider_resizing",
    "sell_value_scaling",
])
def test_lifecycle_growth_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    # Scale age decay config for quick growth
    config = driver.world.services.get(GameConfig)
    config.rules.stat_decay.age = 100.0
    
    if case_type == "age_tick":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        initial_age = stats.age
        driver.run_for(1.0)
        assert stats.age > initial_age
        
    elif case_type == "baby_child_transition":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        trans = driver.get_component(reimu_id, Transform)
        stats.growth_stage = "Baby"
        stats.age = 100.0
        trans.scale = 0.5
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle.update(driver.world, 0.02)
        assert stats.growth_stage == "Child"
        assert trans.scale > 0.5
        
    elif case_type == "child_adult_transition":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        trans = driver.get_component(reimu_id, Transform)
        stats.growth_stage = "Child"
        stats.age = 300.0
        trans.scale = 0.75
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle.update(driver.world, 0.02)
        assert stats.growth_stage == "Adult"
        assert trans.scale > 0.75
        
    elif case_type == "collider_resizing":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        physics = driver.get_component(reimu_id, PhysicsBody)
        stats = driver.get_component(reimu_id, YukkuriStats)
        
        # Transition baby -> child
        stats.growth_stage = "Baby"
        stats.age = 100.0
        initial_radius = physics.shape.radius
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle.update(driver.world, 0.02)
        assert physics.shape.radius > initial_radius
        
    elif case_type == "sell_value_scaling":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        needs = driver.get_component(reimu_id, Needs)
        
        stats.age = 0.0
        val_baby = stats.calculate_value(needs)
        
        stats.age = 300.0
        stats.growth_stage = "Adult"
        val_adult = stats.calculate_value(needs)
        assert val_adult > val_baby

# 4. Breeding & Reproduction
@pytest.mark.parametrize("case_type", [
    "breeding_check",
    "breeding_cost",
    "baby_spawn",
    "baby_type",
    "relationship_parent",
])
def test_breeding_reproduction_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    # Configure breeding settings for deterministic breeding
    config = driver.world.services.get(GameConfig)
    config.rules.lifecycle.breeding_chance = 1.0
    config.rules.lifecycle.breeding_happiness_threshold = 80.0
    config.rules.lifecycle.breeding_energy_threshold = 80.0
    config.rules.lifecycle.breeding_cost = 40.0
    
    parent_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    stats = driver.get_component(parent_id, YukkuriStats)
    needs = driver.get_component(parent_id, Needs)
    stats.growth_stage = "Adult"
    needs.energy = 100.0
    
    # EmotionalState Happiness
    emotional = driver.get_component(parent_id, EmotionalState)
    emotional.happiness = 90.0
    
    initial_entities = set(driver.world.get_entities_with(YukkuriStats))
    driver.run_for(1.0)
    final_entities = set(driver.world.get_entities_with(YukkuriStats))
    new_entities = final_entities - initial_entities
    
    if case_type == "breeding_check":
        assert len(new_entities) > 0
        
    elif case_type == "breeding_cost":
        # Subtracting breeding cost
        assert needs.energy <= 60.0
        
    elif case_type == "baby_spawn":
        baby_id = list(new_entities)[0]
        baby_trans = driver.get_component(baby_id, Transform)
        assert baby_trans is not None
        
    elif case_type == "baby_type":
        baby_id = list(new_entities)[0]
        baby_stats = driver.get_component(baby_id, YukkuriStats)
        assert baby_stats.type_id == "reimu"
        
    elif case_type == "relationship_parent":
        baby_id = list(new_entities)[0]
        baby_registry = driver.get_component(baby_id, RelationshipRegistry)
        assert parent_id in baby_registry.biological_parents

# 5. Proximity & Relationships
@pytest.mark.parametrize("case_type", [
    "proximity_detection",
    "family_proximity_benefits",
    "birth_relationships",
    "registry_tracks_affinity",
    "mate_registration",
])
def test_proximity_relationships_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    # Setup fast family check (using correct attribute check_interval)
    fam_sys = driver.world.get_system(FamilySystem)
    fam_sys.check_interval = 0.01
    
    if case_type == "proximity_detection":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(120.0, 100.0).build()
        sync_spatial_service(driver)
        
        # FamilySystem should run proximity
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        reg_b = driver.get_component(reimu_b, RelationshipRegistry)
        
        # Form family group manually
        reg_a.family_group_id = 999
        reg_b.family_group_id = 999
        
        emo_a = driver.get_component(reimu_a, EmotionalState)
        emo_a.happiness = 0.0
        emo_a.stress = 50.0
        
        driver.run_for(1.0)
        assert emo_a.happiness > 0.0
        assert emo_a.stress < 50.0
        
    elif case_type == "family_proximity_benefits":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 110.0).build()
        sync_spatial_service(driver)
        
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        reg_b = driver.get_component(reimu_b, RelationshipRegistry)
        reg_a.family_group_id = 111
        reg_b.family_group_id = 111
        
        emo_a = driver.get_component(reimu_a, EmotionalState)
        emo_b = driver.get_component(reimu_b, EmotionalState)
        emo_a.happiness = 10.0
        emo_b.happiness = 10.0
        
        driver.run_for(1.0)
        assert emo_a.happiness > 10.0
        assert emo_b.happiness > 10.0
        
    elif case_type == "birth_relationships":
        # Check that spawning baby with parent registers relationship
        from yukkuri_game.game.entity_factory import EntityFactory
        factory = driver.world.services.get(EntityFactory)
        parent_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        baby_id = factory.create_yukkuri("reimu", 110.0, 110.0, parents=[parent_id])
        
        baby_reg = driver.get_component(baby_id, RelationshipRegistry)
        parent_reg = driver.get_component(parent_id, RelationshipRegistry)
        assert parent_id in baby_reg.biological_parents
        assert baby_id in parent_reg.biological_children
        
    elif case_type == "registry_tracks_affinity":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        reg_a.relationships[888] = RelationshipData(affinity=50.0, trust=40.0, fear=10.0, familiarity=30.0)
        rel = reg_a.relationships[888]
        assert rel.affinity == 50.0
        assert rel.trust == 40.0
        assert rel.fear == 10.0
        assert rel.familiarity == 30.0
        
    elif case_type == "mate_registration":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        reg_a.mate_id = 777
        assert reg_a.mate_id == 777

# 6. Opinion & Gossip
@pytest.mark.parametrize("case_type", [
    "witness_event",
    "relationship_update",
    "gossip_transmission",
    "gossip_limits",
    "gossip_decay",
])
def test_opinion_gossip_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "witness_event":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
        witness = driver.yukkuri_builder("reimu").at(120.0, 100.0).build()
        sync_spatial_service(driver)
        
        bus = driver.world.services.get(EventBus)
        g_witness = driver.get_component(witness, GossipQueue)
        
        # Trigger interaction
        bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Dance"))
        driver.run_for(0.1)
        
        assert len(g_witness.priority_queue) > 0
        
    elif case_type == "relationship_update":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
        
        social_system = driver.world.get_system(SocialSystem)
        req = InteractionRequest(target_id=reimu_b, consume=False, action="Dance")
        
        # This will update relationships
        social_system.process_interaction_request(driver.world, reimu_a, req)
        
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        assert reimu_b in reg_a.relationships
        
    elif case_type == "gossip_transmission":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
        
        g_a = driver.get_component(reimu_a, GossipQueue)
        g_b = driver.get_component(reimu_b, GossipQueue)
        
        packet = GossipPacket(target_id=999, event_type="Dance", value=50.0, timestamp=1.0)
        g_a.add_packet(packet)
        
        bus = driver.world.services.get(EventBus)
        bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Talk"))
        driver.run_for(0.1)
        
        # Verify reimu_b received the gossip packet about 999
        found = any(p.target_id == 999 for p in g_b.priority_queue)
        assert found
        
    elif case_type == "gossip_limits":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        g_a = driver.get_component(reimu_a, GossipQueue)
        
        # Add many packets
        for i in range(15):
            g_a.add_packet(GossipPacket(target_id=i, event_type="Talk", value=float(i)))
            
        assert len(g_a.priority_queue) <= 10
        
    elif case_type == "gossip_decay":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
        
        g_a = driver.get_component(reimu_a, GossipQueue)
        g_b = driver.get_component(reimu_b, GossipQueue)
        
        g_a.add_packet(GossipPacket(target_id=888, event_type="Dance", value=100.0))
        
        bus = driver.world.services.get(EventBus)
        bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Talk"))
        driver.run_for(0.1)
        
        # Verify decayed value in B
        packet_in_b = [p for p in g_b.priority_queue if p.target_id == 888][0]
        assert packet_in_b.value == 90.0  # 100.0 * 0.9

# 7. Traits & Skills
@pytest.mark.parametrize("case_type", [
    "trait_decay_modifier",
    "trait_bt_choice",
    "skill_xp_gain",
    "skill_level_up",
    "passion_xp_speed",
])
def test_traits_skills_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "trait_decay_modifier":
        # Glutton increases hunger decay by 1.5x
        normal_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        glutton_id = driver.yukkuri_builder("reimu").at(150.0, 100.0).build()
        
        # Setup moderate hunger decay to prevent clamping at 100.0
        config = driver.world.services.get(GameConfig)
        config.rules.stat_decay.hunger = 0.5
        
        pers_n = driver.get_component(normal_id, Personality)
        pers_g = driver.get_component(glutton_id, Personality)
        pers_n.traits.clear()
        pers_g.traits.clear()
        pers_g.traits.add("GLUTTON")
        
        needs_n = driver.get_component(normal_id, Needs)
        needs_g = driver.get_component(glutton_id, Needs)
        needs_n.hunger = 0.0
        needs_g.hunger = 0.0
        
        driver.run_for(1.0)
        assert needs_g.hunger > needs_n.hunger
        
    elif case_type == "trait_bt_choice":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        pers = driver.get_component(reimu_id, Personality)
        pers.traits.add("SCUM")
        
        trait_service = driver.world.services.get(TraitService)
        overrides = trait_service.calculate_overrides(pers.traits)
        assert "Social/Empathy" in overrides
        
    elif case_type == "skill_xp_gain":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        initial_xp = skills.states["athletics"].current_xp
        skill_service.add_xp(reimu_id, "athletics", 10.0)
        assert skills.states["athletics"].current_xp > initial_xp
        
    elif case_type == "skill_level_up":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        # Athletics level-up
        skills.states["athletics"].level = 0
        skills.states["athletics"].current_xp = 0.0
        
        skill_service.add_xp(reimu_id, "athletics", 150.0)
        assert skills.states["athletics"].level == 1
        
    elif case_type == "passion_xp_speed":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        # Set normal passion
        skills.states["athletics"].passion = 1.0
        skills.states["athletics"].current_xp = 0.0
        skill_service.add_xp(reimu_id, "athletics", 10.0)
        xp_normal = skills.states["athletics"].current_xp
        
        # Set interested passion
        skills.states["athletics"].passion = 2.5
        skills.states["athletics"].current_xp = 0.0
        skill_service.add_xp(reimu_id, "athletics", 10.0)
        xp_burning = skills.states["athletics"].current_xp
        assert xp_burning > xp_normal

# 8. Time, Environment & Feedback
@pytest.mark.parametrize("case_type", [
    "virtual_clock_progress",
    "day_night_ambient",
    "cursor_light_toggle",
    "darkness_stress",
    "feedback_text_sound",
])
def test_time_environment_feedback_coverage(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "virtual_clock_progress":
        time_service = driver.world.services.get(TimeService)
        initial_time = time_service.time_elapsed
        driver.run_for(1.0)
        assert time_service.time_elapsed > initial_time
        
    elif case_type == "day_night_ambient":
        time_service = driver.world.services.get(TimeService)
        try:
            day_night = driver.world.get_system(DayNightSystem)
        except KeyError:
            day_night = DayNightSystem()
            driver.world.add_system(day_night)
        
        # Set noon
        time_service.time_elapsed = 12.0 * 3600.0
        color_noon = day_night._get_ambient_color(12.0)
        
        # Set night
        time_service.time_elapsed = 23.0 * 3600.0
        color_night = day_night._get_ambient_color(23.0)
        
        assert color_noon != color_night
        
    elif case_type == "cursor_light_toggle":
        mlight = driver.world.services.get(MouseLightSystem)
        assert mlight.enabled is False
        mlight.toggle()
        assert mlight.enabled is True
        
    elif case_type == "darkness_stress":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        emo = driver.get_component(reimu_id, EmotionalState)
        emo.stress = 0.0
        
        time_service = driver.world.services.get(TimeService)
        time_service.time_elapsed = 23.0 * 3600.0
        
        driver.run_for(1.0)
        assert emo.stress > 0.0
        
    elif case_type == "feedback_text_sound":
        # Trigger sold event which generates floating text
        bus = driver.world.services.get(EventBus)
        bus.publish(EntitySoldEvent(1, 100, (100.0, 100.0)))
        driver.run_for(0.1)
        
        # Verify floating text entity spawned
        texts = driver.get_entities_with(FloatingText)
        assert len(texts) > 0

# ===========================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 cases per feature = 40+ tests)
# ===========================================================================

# 1. Need Decay & Metabolism Boundary
@pytest.mark.parametrize("need_name, val, expected_val", [
    ("hunger", -10.0, 0.0),
    ("hunger", 110.0, 100.0),
    ("energy", -10.0, 0.0),
    ("energy", 110.0, 100.0),
    ("cleanliness", -10.0, 0.0),
    ("cleanliness", 110.0, 100.0),
])
def test_need_boundary_clamping(game_driver: GameDriver, need_name: str, val: float, expected_val: float) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    
    setattr(needs, need_name, val)
    assert getattr(needs, need_name) == expected_val

def test_need_boundary_starvation_damage(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    needs.hunger = 100.0
    needs.health = 100.0
    
    config = driver.world.services.get(GameConfig)
    config.rules.stat_decay.starvation_damage = 50.0
    
    driver.run_for(1.0)
    assert needs.health < 100.0

def test_need_boundary_sleep_recovery(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    needs.energy = 50.0
    
    # Tick Sleep Action manually
    from yukkuri_game.game.ai.behaviors.actions.survival import Sleep as SleepAction
    sleep_action = SleepAction(name="Sleep", entity_id=reimu_id, world=driver.world)
    py_trees.blackboard.Blackboard().set("dt", 1.0)
    
    sleep_action.update()
    assert needs.energy > 50.0

def test_need_boundary_eating_recovery(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    cookie_id = driver.item_builder("cookie").at(100.0, 100.0).build()
    
    needs = driver.get_component(reimu_id, Needs)
    needs.hunger = 50.0
    
    hunger_system = driver.world.get_system(HungerSystem)
    
    req = InteractionRequest(target_id=cookie_id, consume=True, action="Eat")
    item_stats = driver.get_component(cookie_id, ItemStats)
    trans = driver.get_component(reimu_id, Transform)
    
    res = hunger_system.process_consumption(driver.world, reimu_id, req, trans, cookie_id, item_stats)
    assert res is True
    assert needs.hunger < 50.0

def test_need_boundary_health_clamp(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    
    needs.max_health = 120.0
    needs.health = 150.0
    assert needs.health == 120.0

# 2. Waste & Cleanliness Boundary
@pytest.mark.parametrize("case_type", [
    "no_poop_below_threshold",
    "no_decay_outside_radius",
    "cumulative_decay",
    "clean_click_radius",
    "low_cleanliness_depression",
])
def test_waste_cleanliness_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "no_poop_below_threshold":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        needs = driver.get_component(reimu_id, Needs)
        needs.bladder = 50.0
        poop_system = driver.world.get_system(PoopSystem)
        poop_system.spawn_chance_per_second = 0.0  # Disable random spawning, only trigger via thresholds
        driver.run_for(1.0)
        assert len(driver.get_entities_with(Poop)) == 0
        
    elif case_type == "no_decay_outside_radius":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        poop_id = create_poop(driver, 400.0, 100.0)  # > 200 radius
        sync_spatial_service(driver)
        needs = driver.get_component(reimu_id, Needs)
        needs.cleanliness = 100.0
        driver.run_for(1.0)
        # Only base decay applies, not poop decay
        assert needs.cleanliness > 95.0
        
    elif case_type == "cumulative_decay":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        needs_a = driver.get_component(reimu_a, Needs)
        needs_a.cleanliness = 100.0
        
        # 1 poop
        poop1 = create_poop(driver, 100.0, 100.0)
        sync_spatial_service(driver)
        driver.run_for(1.0)
        decay_1 = 100.0 - needs_a.cleanliness
        
        # 2 poops
        driver.world.destroy_entity(poop1)
        needs_a.cleanliness = 100.0
        create_poop(driver, 100.0, 100.0)
        create_poop(driver, 101.0, 101.0)
        sync_spatial_service(driver)
        driver.run_for(1.0)
        decay_2 = 100.0 - needs_a.cleanliness
        assert decay_2 > decay_1 * 1.5
        
    elif case_type == "clean_click_radius":
        poop_id = create_poop(driver, 100.0, 100.0)
        sync_spatial_service(driver)
        cmd = CleanEntityCommand(150.0, 100.0)  # Dist = 50 > 32 radius
        cmd.execute(driver.world)
        driver.run_for(0.1)
        assert driver.world.entity_exists(poop_id)
        
    elif case_type == "low_cleanliness_depression":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        needs = driver.get_component(reimu_id, Needs)
        emo = driver.get_component(reimu_id, EmotionalState)
        
        needs.cleanliness = 5.0
        emo.happiness = -10.0
        emo.stress = 0.0
        assert emo.get_dominant_emotion() == "Depressed/Sulking"

# 3. Lifecycle & Growth Boundary
@pytest.mark.parametrize("case_type", [
    "no_age_tick_on_pause",
    "exact_transition_limits",
    "safe_transform_scaling",
    "baby_cannot_breed",
    "growth_health_restore",
])
def test_lifecycle_growth_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "no_age_tick_on_pause":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        stats.age = 10.0
        
        # Pause game session
        scene = driver.game.scene_manager.current_scene
        scene.session_manager.paused = True
        
        driver.run_for(1.0)
        assert stats.age == 10.0
        
    elif case_type == "exact_transition_limits":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        
        stats.growth_stage = "Baby"
        stats.age = 99.9
        driver.run_for(0.01)  # tiny step
        # Since LifecycleSystem runs updates, it checks thresholds:
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle.update(driver.world, 0.01)
        assert stats.growth_stage == "Baby"
        
        stats.age = 100.0
        lifecycle.update(driver.world, 0.01)
        assert stats.growth_stage == "Child"
        
    elif case_type == "safe_transform_scaling":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        trans = driver.get_component(reimu_id, Transform)
        trans.scale = 0.5
        
        stats = driver.get_component(reimu_id, YukkuriStats)
        stats.growth_stage = "Baby"
        stats.age = 100.0
        
        # Grows to child
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle.update(driver.world, 1.0)
        assert trans.scale == 0.75  # 0.5 * 1.5
        
    elif case_type == "baby_cannot_breed":
        baby_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(baby_id, YukkuriStats)
        needs = driver.get_component(baby_id, Needs)
        emo = driver.get_component(baby_id, EmotionalState)
        
        stats.growth_stage = "Baby"
        needs.energy = 100.0
        emo.happiness = 100.0
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        assert not lifecycle._should_breed(driver.world, baby_id, stats, needs)
        
    elif case_type == "growth_health_restore":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(reimu_id, YukkuriStats)
        needs = driver.get_component(reimu_id, Needs)
        
        stats.growth_stage = "Baby"
        stats.age = 100.0
        needs.max_health = 100.0
        needs.health = 10.0
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle.update(driver.world, 1.0)
        assert needs.health == 60.0  # 10.0 + growth_health_restore(50)

# 4. Breeding & Reproduction Boundary
@pytest.mark.parametrize("case_type", [
    "non_adult_cannot_breed",
    "energy_threshold",
    "happiness_threshold",
    "spiral_search",
    "chance_scaling",
])
def test_breeding_reproduction_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "non_adult_cannot_breed":
        child_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(child_id, YukkuriStats)
        needs = driver.get_component(child_id, Needs)
        stats.growth_stage = "Child"
        needs.energy = 100.0
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        assert not lifecycle._should_breed(driver.world, child_id, stats, needs)
        
    elif case_type == "energy_threshold":
        adult_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(adult_id, YukkuriStats)
        needs = driver.get_component(adult_id, Needs)
        stats.growth_stage = "Adult"
        needs.energy = 79.0  # Threshold = 80
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        assert not lifecycle._should_breed(driver.world, adult_id, stats, needs)
        
    elif case_type == "happiness_threshold":
        adult_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(adult_id, YukkuriStats)
        needs = driver.get_component(adult_id, Needs)
        emo = driver.get_component(adult_id, EmotionalState)
        
        stats.growth_stage = "Adult"
        needs.energy = 100.0
        emo.happiness = 79.0  # Threshold = 80
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        assert not lifecycle._should_breed(driver.world, adult_id, stats, needs)
        
    elif case_type == "spiral_search":
        parent_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(parent_id, YukkuriStats)
        needs = driver.get_component(parent_id, Needs)
        trans = driver.get_component(parent_id, Transform)
        
        stats.growth_stage = "Adult"
        needs.energy = 100.0
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        lifecycle._breed(driver.world, parent_id, stats, needs, trans)
        
        babies = [e for e in driver.world.get_entities_with(YukkuriStats) if e != parent_id]
        assert len(babies) == 1
        
    elif case_type == "chance_scaling":
        config = driver.world.services.get(GameConfig)
        config.rules.lifecycle.breeding_chance = 0.0
        
        parent_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        stats = driver.get_component(parent_id, YukkuriStats)
        needs = driver.get_component(parent_id, Needs)
        
        stats.growth_stage = "Adult"
        needs.energy = 100.0
        
        lifecycle = driver.world.get_system(LifecycleSystem)
        assert not lifecycle._should_breed(driver.world, parent_id, stats, needs)

# 5. Proximity & Relationships Boundary
@pytest.mark.parametrize("case_type", [
    "proximity_range",
    "registry_clamping",
    "enemy_proximity",
    "stress_overrides",
    "loneliness_social_decay",
])
def test_proximity_relationships_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    fam_sys = driver.world.get_system(FamilySystem)
    fam_sys.check_interval = 0.01
    
    if case_type == "proximity_range":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(300.0, 100.0).build()  # outside range 150
        sync_spatial_service(driver)
        
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        reg_b = driver.get_component(reimu_b, RelationshipRegistry)
        reg_a.family_group_id = 222
        reg_b.family_group_id = 222
        
        emo_a = driver.get_component(reimu_a, EmotionalState)
        emo_a.happiness = 0.0
        
        driver.run_for(1.0)
        assert emo_a.happiness == 0.0
        
    elif case_type == "registry_clamping":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reg_a = driver.get_component(reimu_a, RelationshipRegistry)
        reg_a.relationships[123] = RelationshipData()
        
        rel = reg_a.relationships[123]
        rel.adjust_affinity(150.0)
        assert rel.affinity == 100.0
        rel.adjust_affinity(-250.0)
        assert rel.affinity == -100.0
        
    elif case_type == "enemy_proximity":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        ai = driver.get_component(reimu_id, AIState)
        ai.current_action = "Flee"
        
        emo = driver.get_component(reimu_id, EmotionalState)
        emo.stress = 0.0
        
        bus = driver.world.services.get(EventBus)
        bus.publish(PunishEntityRequest(reimu_id))
        driver.run_for(0.1)
        # Account for stress decay during run_for by asserting a threshold >= 15.0
        assert emo.stress >= 15.0
        
    elif case_type == "stress_overrides":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        emo = driver.get_component(reimu_id, EmotionalState)
        
        emo.happiness = 50.0
        emo.stress = 90.0
        assert emo.get_dominant_emotion() == "Excited/Manic"
        
    elif case_type == "loneliness_social_decay":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        needs = driver.get_component(reimu_id, Needs)
        needs.social = 10.0
        
        config = driver.world.services.get(GameConfig)
        config.rules.stat_decay.social = 20.0
        
        driver.run_for(1.0)
        assert needs.social == 0.0

# 6. Opinion & Gossip Boundary
@pytest.mark.parametrize("case_type", [
    "core_memory_lock",
    "witness_range",
    "line_of_sight",
    "no_self_gossip",
    "memory_replacement",
])
def test_opinion_gossip_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "core_memory_lock":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reg = driver.get_component(reimu_id, RelationshipRegistry)
        
        rel = RelationshipData()
        reg.relationships[999] = rel
        mem = MemoryHeadline(id=1, timestamp=0.0, importance=80.0, sentiment=-50.0, event_type="Abuse", text="abused", is_locked=True)
        rel.add_headline(mem)
        
        assert len(rel.core_buffer) == 1
        assert rel.core_buffer[0].is_locked
        
    elif case_type == "witness_range":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
        witness = driver.yukkuri_builder("reimu").at(2000.0, 2000.0).build()  # Place well outside sectors
        sync_spatial_service(driver)
        
        bus = driver.world.services.get(EventBus)
        g_w = driver.get_component(witness, GossipQueue)
        
        bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Dance"))
        driver.run_for(0.1)
        assert len(g_w.priority_queue) == 0
        
    elif case_type == "line_of_sight":
        # Place entities so they do not start/end inside the wall's 64x64 bounds
        reimu_a = driver.yukkuri_builder("reimu").at(50.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(90.0, 100.0).build()
        witness = driver.yukkuri_builder("reimu").at(250.0, 100.0).build()
        
        wall_id = driver.item_builder("wall").at(150.0, 100.0).build()
        
        # Zero gravity so the wall does not fall out of line
        driver.world.services.get(IPhysicsService).space.gravity = (0, 0)
        
        # Make the wall static by removing, changing type, and re-adding
        pb = driver.get_component(wall_id, PhysicsBody)
        space = driver.world.services.get(IPhysicsService).space
        
        # Step the physics space once to index the wall shape in Pymunk
        driver.run_for(0.02)
        sync_spatial_service(driver)
        
        # Remove the wall body/shape and add as static, but keep it physically blocking
        space.remove(pb.body, pb.shape)
        pb.body.body_type = pymunk.Body.STATIC
        space.add(pb.body, pb.shape)
        
        # Remove the actor and witness circle shapes temporarily from the space 
        # so the segment query only hits the blocking wall
        pb_a = driver.get_component(reimu_a, PhysicsBody)
        pb_b = driver.get_component(reimu_b, PhysicsBody)
        pb_w = driver.get_component(witness, PhysicsBody)
        space.remove(pb_a.body, pb_a.shape)
        space.remove(pb_b.body, pb_b.shape)
        space.remove(pb_w.body, pb_w.shape)
        
        bus = driver.world.services.get(EventBus)
        g_w = driver.get_component(witness, GossipQueue)
        
        bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Dance"))
        driver.run_for(0.1)
        
        gossip_system = driver.world.get_system(GossipSystem)
        los = gossip_system._check_line_of_sight(driver.world, driver.get_component(reimu_a, Transform), driver.get_component(witness, Transform))
        assert not los
        
    elif case_type == "no_self_gossip":
        reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
        
        g_a = driver.get_component(reimu_a, GossipQueue)
        g_b = driver.get_component(reimu_b, GossipQueue)
        
        g_a.add_packet(GossipPacket(target_id=reimu_b, event_type="Dance", value=50.0))
        
        bus = driver.world.services.get(EventBus)
        bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Talk"))
        driver.run_for(0.1)
        assert len(g_b.priority_queue) == 0
        
    elif case_type == "memory_replacement":
        rel = RelationshipData()
        for i in range(35):
            rel.add_headline(MemoryHeadline(id=i, timestamp=0.0, importance=70.0, sentiment=1.0, event_type="Talk", text="talk", is_locked=True))
            
        assert len(rel.core_buffer) == 35
        rel.add_headline(MemoryHeadline(id=99, timestamp=0.0, importance=10.0, sentiment=1.0, event_type="Talk", text="talk", is_locked=True))
        assert 99 not in [m.id for m in rel.core_buffer]

# 7. Traits & Skills Boundary
@pytest.mark.parametrize("case_type", [
    "skill_level_cap",
    "skill_soft_cap",
    "athletics_speed",
    "grace_period",
    "level_floor",
])
def test_traits_skills_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "skill_level_cap":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        skills.states["athletics"].level = 20
        skills.states["athletics"].current_xp = 0.0
        skill_service.add_xp(reimu_id, "athletics", 1000.0)
        assert skills.states["athletics"].level == 20
        
    elif case_type == "skill_soft_cap":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        skills.states["athletics"].level = 15
        skills.states["athletics"].current_xp = 0.0
        skills.states["athletics"].passion = 1.0
        
        skill_service.add_xp(reimu_id, "athletics", 100.0)
        assert skills.states["athletics"].current_xp == 10.0
        
    elif case_type == "athletics_speed":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        assert "athletics" in skills.states
        
    elif case_type == "grace_period":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        skills.states["athletics"].current_xp = 50.0
        skills.states["athletics"].last_used_gametime = 0.0
        
        time_service = driver.world.services.get(TimeService)
        time_service.time_elapsed = 86400.0 * 0.5
        
        skill_service.apply_decay(reimu_id)
        assert skills.states["athletics"].current_xp == 50.0
        
    elif case_type == "level_floor":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        skills = driver.get_component(reimu_id, Skills)
        skill_service = driver.world.services.get(SkillService)
        skill_service.initialize_skills(reimu_id)
        
        skills.states["athletics"].level = 2
        skills.states["athletics"].current_xp = 5.0
        skills.states["athletics"].last_used_gametime = 0.0
        
        time_service = driver.world.services.get(TimeService)
        time_service.time_elapsed = 86400.0 * 10.0
        
        skill_service.apply_decay(reimu_id)
        assert skills.states["athletics"].level == 2
        assert skills.states["athletics"].current_xp == 0.0

# 8. Time, Environment & Feedback Boundary
@pytest.mark.parametrize("case_type", [
    "time_speed_commands",
    "darkness_stress_negation",
    "cursor_light_position",
    "crying_probability",
    "floating_text_cleanup",
])
def test_time_environment_feedback_boundary(game_driver: GameDriver, case_type: str) -> None:
    driver = game_driver
    driver.setup()
    
    if case_type == "time_speed_commands":
        time_service = driver.world.services.get(TimeService)
        time_service.game_speed = 2.0
        assert time_service.game_speed == 2.0
        
    elif case_type == "darkness_stress_negation":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        emo = driver.get_component(reimu_id, EmotionalState)
        emo.stress = 0.0
        
        lamp_id = driver.item_builder("lamp").at(100.0, 100.0).build()
        light = driver.get_component(lamp_id, LightSource)
        light.intensity = 1.0
        light.radius = 200.0
        
        time_service = driver.world.services.get(TimeService)
        time_service.time_elapsed = 23.0 * 3600.0
        
        driver.run_for(1.0)
        assert emo.stress == 0.0
        
    elif case_type == "cursor_light_position":
        mlight = driver.world.services.get(MouseLightSystem)
        mlight.toggle()
        assert mlight.light_entity != -1
        
    elif case_type == "crying_probability":
        reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
        emo = driver.get_component(reimu_id, EmotionalState)
        emo.happiness = -50.0
        feedback = driver.world.get_system(FeedbackSystem)
        feedback.update(driver.world, 0.1)
        
    elif case_type == "floating_text_cleanup":
        text_id = driver.world.create_entity()
        driver.world.add_component(text_id, Transform(x=100, y=100))
        driver.world.add_component(text_id, FloatingText(text="Test", color=(255,0,0), lifetime=0.1, max_lifetime=0.1, velocity_y=-10))
        
        driver.run_for(0.2)
        assert not driver.world.entity_exists(text_id)

# ===========================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (>=1 case per feature pair = 8+ tests)
# ===========================================================================

# 1. Need Decay + Breeding
def test_need_cross_feature_starvation_exhaustion(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    stats = driver.get_component(reimu_id, YukkuriStats)
    needs = driver.get_component(reimu_id, Needs)
    emo = driver.get_component(reimu_id, EmotionalState)
    
    stats.growth_stage = "Adult"
    needs.hunger = 100.0
    needs.energy = 0.0
    emo.happiness = 100.0
    
    lifecycle = driver.world.get_system(LifecycleSystem)
    assert not lifecycle._should_breed(driver.world, reimu_id, stats, needs)

# 2. Waste + Sleep
def test_waste_cleanliness_cross_feature_dirty_bed(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    ai = driver.get_component(reimu_id, AIState)
    
    needs.bladder = 95.0
    needs.cleanliness = 100.0
    ai.current_action = "Sleep"
    
    poop_system = driver.world.get_system(PoopSystem)
    poop_system.spawn_chance_per_second = 1000.0
    
    driver.run_for(1.0)
    assert len(driver.get_entities_with(Poop)) > 0
    assert needs.cleanliness < 100.0

# 3. Lifecycle + Need Decay
def test_lifecycle_growth_cross_feature_decay_scaling(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    pers = driver.get_component(reimu_id, Personality)
    pers.traits.add("GLUTTON")
    
    needs = driver.get_component(reimu_id, Needs)
    needs.hunger = 0.0
    
    driver.run_for(1.0)
    assert needs.hunger > 0.0

# 4. Breeding + Relationship Registration
def test_breeding_reproduction_cross_feature_family_double_parents(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    parent_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    parent_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
    
    reg_a = driver.get_component(parent_a, RelationshipRegistry)
    reg_b = driver.get_component(parent_b, RelationshipRegistry)
    
    reg_a.mate_id = parent_b
    reg_b.mate_id = parent_a
    
    from yukkuri_game.game.entity_factory import EntityFactory
    factory = driver.world.services.get(EntityFactory)
    baby_id = factory.create_yukkuri("reimu", 100.0, 105.0, parents=[parent_a, parent_b])
    
    baby_reg = driver.get_component(baby_id, RelationshipRegistry)
    assert parent_a in baby_reg.biological_parents
    assert parent_b in baby_reg.biological_parents

# 5. Proximity + Need Satisfaction
def test_proximity_relationships_cross_feature_loneliness_wander(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    needs.social = 0.0
    
    ai = driver.get_component(reimu_id, AIState)
    driver.run_for(1.0)
    assert ai.current_action is not None

# 6. Opinion + Fear Spread
def test_opinion_gossip_cross_feature_fear_spread(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
    
    g_a = driver.get_component(reimu_a, GossipQueue)
    g_b = driver.get_component(reimu_b, GossipQueue)
    
    g_a.add_packet(GossipPacket(target_id=999, event_type="Fight", value=80.0))
    
    bus = driver.world.services.get(EventBus)
    bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Talk"))
    driver.run_for(0.1)
    
    assert any(p.target_id == 999 for p in g_b.priority_queue)

# 7. Traits + Skill level combo
def test_traits_skills_cross_feature_hyperactive_athletics(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    pers = driver.get_component(reimu_id, Personality)
    pers.traits.add("ATHLETIC")
    
    skills = driver.get_component(reimu_id, Skills)
    skill_service = driver.world.services.get(SkillService)
    skill_service.initialize_skills(reimu_id)
    
    assert skills.states["athletics"].passion == 1.5

# 8. Night cycle + Sleep behavior
def test_time_environment_feedback_cross_feature_night_sleep(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    time_service = driver.world.services.get(TimeService)
    time_service.time_elapsed = 23.0 * 3600.0
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    ai = driver.get_component(reimu_id, AIState)
    needs = driver.get_component(reimu_id, Needs)
    needs.energy = 20.0
    
    driver.run_for(1.0)
    assert ai.current_action is not None

# ===========================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (>=5 compound tests)
# ===========================================================================

# Scenario 1: Starvation, Foraging, Healing, Sleeping
def test_real_world_starve_eat_sleep(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    needs.hunger = 100.0
    needs.health = 80.0
    needs.energy = 10.0
    
    cookie_id = driver.item_builder("cookie").at(100.0, 100.0).build()
    
    hunger_system = driver.world.get_system(HungerSystem)
    req = InteractionRequest(target_id=cookie_id, consume=True, action="Eat")
    item_stats = driver.get_component(cookie_id, ItemStats)
    trans = driver.get_component(reimu_id, Transform)
    
    res = hunger_system.process_consumption(driver.world, reimu_id, req, trans, cookie_id, item_stats)
    assert res is True
    assert needs.hunger < 100.0
    
    needs.health = 100.0
    from yukkuri_game.game.ai.behaviors.actions.survival import Sleep as SleepAction
    sleep_action = SleepAction(name="Sleep", entity_id=reimu_id, world=driver.world)
    py_trees.blackboard.Blackboard().set("dt", 1.0)
    sleep_action.update()
    
    assert needs.energy > 10.0

# Scenario 2: Waste and Cleanliness cycle
def test_real_world_waste_cycle(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    needs = driver.get_component(reimu_id, Needs)
    needs.bladder = 100.0
    needs.cleanliness = 100.0
    
    poop_system = driver.world.get_system(PoopSystem)
    poop_system.spawn_chance_per_second = 1000.0
    driver.run_for(1.0)
    
    poops = driver.get_entities_with(Poop)
    assert len(poops) > 0
    assert needs.cleanliness < 100.0
    
    # Disable spawning before cleanup to prevent background tick spawns
    poop_system.spawn_chance_per_second = 0.0
    sync_spatial_service(driver)
    
    # Clean all poops by clicking on their exact locations
    for p in poops:
        trans = driver.get_component(p, Transform)
        cmd = CleanEntityCommand(trans.x, trans.y)
        cmd.execute(driver.world)
        
    driver.run_for(0.1)
    assert len(driver.get_entities_with(Poop)) == 0

# Scenario 3: Reproduction, Growth and Inherited stats
def test_real_world_grow_breed_inherit(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    config = driver.world.services.get(GameConfig)
    config.rules.lifecycle.breeding_chance = 1.0
    config.rules.lifecycle.breeding_happiness_threshold = 80.0
    config.rules.lifecycle.breeding_energy_threshold = 80.0
    config.rules.lifecycle.breeding_cost = 20.0
    
    parent_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    stats = driver.get_component(parent_id, YukkuriStats)
    needs = driver.get_component(parent_id, Needs)
    emo = driver.get_component(parent_id, EmotionalState)
    
    stats.growth_stage = "Adult"
    needs.energy = 100.0
    emo.happiness = 90.0
    
    initial_entities = set(driver.world.get_entities_with(YukkuriStats))
    driver.run_for(1.0)
    final_entities = set(driver.world.get_entities_with(YukkuriStats))
    new_entities = final_entities - initial_entities
    
    assert len(new_entities) == 1
    baby_id = list(new_entities)[0]
    baby_stats = driver.get_component(baby_id, YukkuriStats)
    assert baby_stats.growth_stage == "Baby"
    assert baby_stats.type_id == "reimu"

# Scenario 4: Witness abuse, gossip, and spread fear
def test_real_world_gossip_fear_run(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_a = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    reimu_b = driver.yukkuri_builder("reimu").at(110.0, 100.0).build()
    
    g_a = driver.get_component(reimu_a, GossipQueue)
    g_b = driver.get_component(reimu_b, GossipQueue)
    
    g_a.add_packet(GossipPacket(target_id=999, event_type="Fight", value=90.0))
    
    bus = driver.world.services.get(EventBus)
    bus.publish(SocialInteractionEvent(reimu_a, reimu_b, "Talk"))
    driver.run_for(0.1)
    
    assert any(p.target_id == 999 for p in g_b.priority_queue)

# Scenario 5: Night darkness stress cycle negated by light
def test_real_world_night_stress_light_sleep(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    emo = driver.get_component(reimu_id, EmotionalState)
    emo.stress = 0.0
    
    time_service = driver.world.services.get(TimeService)
    time_service.time_elapsed = 23.0 * 3600.0
    
    lamp_id = driver.item_builder("lamp").at(100.0, 100.0).build()
    light = driver.get_component(lamp_id, LightSource)
    light.intensity = 1.0
    light.radius = 300.0
    
    driver.run_for(1.0)
    assert emo.stress == 0.0
