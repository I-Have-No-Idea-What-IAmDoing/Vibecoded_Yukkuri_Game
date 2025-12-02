import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import Skills, SkillState, Personality
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.game.skill_constants import SkillId, PassionLevel
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.services import TimeService

@pytest.fixture
def world():
    w = World()
    # Register necessary services
    time_service = TimeService()
    # Correct usage: register(instance, type)
    w.services.register(time_service, TimeService)

    # Mock TraitService
    trait_service = MagicMock(spec=TraitService)
    trait_service.get_trait.return_value = {}

    # Correct usage: register(instance, type)
    w.services.register(trait_service, TraitService)

    return w

@pytest.fixture
def skill_service(world):
    service = SkillService(world)
    # Inject test data
    service.skills_data = {
        "athletics": {
            "name": "Athletics",
            "max_level": 20,
            "decay_rate": 10.0,
            "soft_cap_base_level": 10
        },
        "socialization": {
             "name": "Socialization",
             "max_level": 20,
             "soft_cap_base_level": 10
        }
    }
    # Register skill service
    world.services.register(service, SkillService)
    return service

def test_initialize_skills(world, skill_service):
    entity = world.create_entity()
    world.add_component(entity, Personality(traits={"ATHLETIC"}))

    # Setup trait mock
    trait_service = world.services.get(TraitService)
    trait_service.get_trait.side_effect = lambda t: {
        "skill_modifiers": {
            "athletics": {"passion_multiplier": 2.5}
        }
    } if t == "ATHLETIC" else {}

    skill_service.initialize_skills(entity)

    skills = world.get_component(entity, Skills)
    assert skills is not None
    assert "athletics" in skills.states
    assert skills.states["athletics"].passion == 2.5
    assert skills.states["socialization"].passion == 1.0 # Default

def test_xp_gain_and_level_up(world, skill_service):
    entity = world.create_entity()
    world.add_component(entity, Skills())
    skill_service.initialize_skills(entity) # Init with default passion

    # Level 0 -> 1 requires 100 XP
    skill_service.add_xp(entity, "athletics", 50.0)
    state = world.get_component(entity, Skills).states["athletics"]
    assert state.level == 0
    assert state.current_xp == 50.0

    skill_service.add_xp(entity, "athletics", 60.0)
    # Total 110. Level up to 1. Remaining 10.
    state = world.get_component(entity, Skills).states["athletics"]
    assert state.level == 1
    assert state.current_xp == 10.0

    # Next level (1 -> 2) requires 100 * 1.5^1 = 150
    req = skill_service.get_xp_required(1)
    assert req == 150.0

def test_soft_cap(world, skill_service):
    entity = world.create_entity()
    world.add_component(entity, Skills())

    # Manually set high level
    skills = world.get_component(entity, Skills)
    state = SkillState(level=12, passion=1.0)
    # Base 10 + 2 = 12. So at level 12, it is >= soft_cap.

    skills.states["athletics"] = state

    # Add XP. Should be reduced by 90% (multiplied by 0.1)
    skill_service.add_xp(entity, "athletics", 100.0)

    # Gain = 100 * 1.0 * 1.0 * 0.1 = 10.0
    assert state.current_xp == 10.0

def test_decay_logic(world, skill_service):
    entity = world.create_entity()
    world.add_component(entity, Skills())

    # Initialize skills with a specific last used time
    skills = world.get_component(entity, Skills)
    state = SkillState(level=5, current_xp=50.0, last_used_gametime=0.0, last_decay_gametime=0.0)
    skills.states["athletics"] = state

    # Decay rate is 10.0 per day. Day is 600s.

    # Simulate time passing: 0.5 days (300s). No decay (since unused < 1.0 day).
    current_time = 300.0
    skill_service.apply_decay(entity, current_time)
    assert state.current_xp == 50.0 # No change
    assert state.last_decay_gametime == 300.0 # Updated tracker

    # Simulate time passing: 1.5 days (900s). Unused for > 1.0 day.
    # Last used 0.0. Current 900.0.
    # Unused duration = 1.5 days.
    # We are in decay zone.
    # last_decay_gametime was 300.0.
    # dt since last decay = 900 - 300 = 600s = 1.0 day.
    # Loss = Rate * dt_days = 10.0 * 1.0 = 10.0.

    current_time = 900.0
    skill_service.apply_decay(entity, current_time)
    assert state.current_xp == 40.0
    assert state.last_decay_gametime == 900.0
