"""
Tests for AI configuration fixes.
"""


from yukkuri_game.engine.application import Application
from yukkuri_game.game.ai.utility import UtilityAIEngine
from yukkuri_game.game.components import RelationshipRegistry
from yukkuri_game.game.components import Skills
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.testing.driver import GameDriver


def test_daytime_sleep_utility() -> None:
    """
    Verifies that Sleep utility for an exhausted Yukkuri during the day is > 0.
    """
    app = Application()
    driver = GameDriver(app)
    driver.setup()

    # Load UtilityAIEngine
    engine = driver.world.services.get(UtilityAIEngine)

    # Context with is_night = 0.0 (daytime) and energy_inv = 100.0 (fully exhausted)
    # Also needs other stats to satisfy needs/stats keys
    context = {
        "energy_inv": 100.0,
        "is_night": 0.0,
        "hunger": 0.0,
        "is_predator": 0.0,
        "happiness_inv": 0.0,
        "constant_100": 100.0,
        "social_inv": 0.0,
        "nearby_friends": 0.0,
        "stress": 0.0,
        "nearby_enemies": 0.0,
        "has_bed": 100.0,
    }

    # Evaluate Sleep action score
    sleep_action = engine.actions["Sleep"]
    score = sleep_action.calculate_utility_compensated(context)

    # Score should be > 0.0, enabling daytime sleep
    assert score > 0.0
    # Specifically, with energy_inv=100.0 -> Tiredness score is ~0.9526.
    # m = 50.0, b = 0.5 with is_night=0.0 -> NightTime score is 0.5.
    # HasBed score is 1.0.
    # Compensated: 1.5 * (0.9526 * 0.5 * 1.0) ** (1/3) = 1.5 * 0.78096 = 1.1714
    # Let's assert score is approximately 1.17
    assert abs(score - 1.1714) < 0.05


def test_socialization_lock_removed() -> None:
    """
    Verifies that a Yukkuri with 0 socialization skill can initiate Talk.
    """
    app = Application()
    driver = GameDriver(app)
    driver.setup()

    # Create actor and target
    actor_id = driver.create_yukkuri("reimu", x=0, y=0)
    target_id = driver.create_yukkuri("marisa", x=20, y=0)

    # Actor has 0 socialization skill
    skills = driver.get_component(actor_id, Skills)
    assert skills is not None
    if "socialization" in skills.states:
        skills.states["socialization"].level = 0.0
    # We should be able to register the interaction without it returning early
    # or being blocked by a conditions constraint.
    social_system = driver.world.get_system(SocialSystem)
    social_system.register_interaction(driver.world, actor_id, target_id, "Talk")
    registry = driver.world.try_get_component(actor_id, RelationshipRegistry)
    assert registry is not None
    assert target_id in registry.relationships

    # Socialization XP should be rewarded
    assert skills.states["socialization"].current_xp > 0.0


def test_data_models_fully_loaded() -> None:
    """
    Verifies that the new fields on YukkuriType, ItemType, and
    InteractionDefinition are loaded correctly and not silently discarded.
    """
    app = Application()
    driver = GameDriver(app)
    driver.setup()

    from yukkuri_game.engine.resource_manager import ResourceManager

    rm = driver.world.services.get(ResourceManager)

    # 1. Test YukkuriType fields (e.g., flandre)
    flandre_type = rm.yukkuri_types.get("flandre")
    assert flandre_type is not None
    assert flandre_type.agility == 1.0
    assert flandre_type.hunger_threshold == 60.0
    assert flandre_type.frame_count == 1
    assert flandre_type.frame_duration == 0.1
    assert flandre_type.loop is True

    # 2. Test ItemType fields (e.g., wall)
    wall_type = rm.item_types.get("wall")
    assert wall_type is not None
    assert wall_type.obstacle_type is None
    assert wall_type.frame_count == 1
    assert wall_type.frame_duration == 0.1
    assert wall_type.loop is True
    assert isinstance(wall_type.animations, dict)

    # 3. Test InteractionDefinition fields (e.g., Talk)
    talk_interaction = rm.interactions.get("Talk")
    assert talk_interaction is not None
    assert talk_interaction.type == "GENERIC"




