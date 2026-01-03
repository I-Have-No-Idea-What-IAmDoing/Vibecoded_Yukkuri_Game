import pytest
import math
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import (
    Skills,
    SkillState,
    Personality,
    YukkuriStats,
)
from yukkuri_game.game.services import TimeService
from yukkuri_game.game.skill_service import SkillService
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_constants import SkillId
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.data_models import SkillDefinition, TraitDefinition


# Mock TraitService for test
class MockTraitService(TraitService):
    def __init__(self, world):
        self.traits = {
            "ATHLETIC": TraitDefinition(
                name="Athletic",
                description="test",
                skill_modifiers={
                    "athletics": {"passion_multiplier": 1.5, "soft_cap_offset": 5.0}
                },
            ),
            "LONER": TraitDefinition(
                name="Loner",
                description="test",
                skill_modifiers={
                    "socialization": {
                        "passion_multiplier": 0.5,
                        "soft_cap_offset": -2.0,
                    }
                },
            ),
        }
        self.interactions = {}

    def load_data(self):
        pass  # Skip loading from files

    def get_trait(self, trait_id):
        return self.traits.get(trait_id)


class MockResourceManager(ResourceManager):
    def __init__(self):
        self.skills = {
            "athletics": SkillDefinition(
                name="Athletics",
                description="test",
                max_level=20,
                decay_rate=10.0,
                soft_cap_base_level=10,
            ),
            "socialization": SkillDefinition(
                name="Socialization",
                description="test",
                max_level=20,
                decay_rate=5.0,
                soft_cap_base_level=10,
            ),
        }
        self.traits = {}
        self.interactions = {}


@pytest.fixture
def world():
    w = World()
    w.services.register(TimeService(), TimeService)

    rm = MockResourceManager()
    w.services.register(rm, ResourceManager)

    # Use real skill service but mock trait service
    w.services.register(MockTraitService(w), TraitService)
    w.services.register(SkillService(w), SkillService)
    return w


def test_skill_initialization(world):
    e = world.create_entity()
    world.add_component(e, Skills())
    world.add_component(e, Personality())
    world.add_component(e, YukkuriStats(name="Test", type_id="test"))

    skill_service = world.services.get(SkillService)
    skill_service.initialize_skills(e)

    skills = world.get_component(e, Skills)
    assert skills is not None
    assert SkillId.ATHLETICS in skills.states
    assert SkillId.SOCIALIZATION in skills.states
    assert skills.states[SkillId.ATHLETICS].level == 0


def test_xp_gain_and_leveling(world):
    e = world.create_entity()
    skills = Skills()
    skills.states[SkillId.ATHLETICS] = SkillState(level=0, current_xp=0.0)
    world.add_component(e, skills)
    world.add_component(e, YukkuriStats(name="Test", type_id="test", discipline=50.0))

    skill_service = world.services.get(SkillService)

    # Required for level 0->1 is 100
    # Gain 50 XP
    skill_service.add_xp(e, SkillId.ATHLETICS, 50.0)
    assert skills.states[SkillId.ATHLETICS].current_xp == 50.0
    assert skills.states[SkillId.ATHLETICS].level == 0

    # Gain another 60 XP (Total 110, should level up)
    skill_service.add_xp(e, SkillId.ATHLETICS, 60.0)

    # 110 - 100 = 10 XP remaining
    # Level should be 1
    assert skills.states[SkillId.ATHLETICS].level == 1
    assert math.isclose(skills.states[SkillId.ATHLETICS].current_xp, 10.0)


def test_trait_modifiers(world):
    e = world.create_entity()
    skills = Skills()
    # Add Athletic trait
    personality = Personality(traits={"ATHLETIC"})
    world.add_component(e, skills)
    world.add_component(e, personality)
    world.add_component(e, YukkuriStats(name="Test", type_id="test", discipline=50.0))

    skill_service = world.services.get(SkillService)
    skill_service.initialize_skills(e)

    # Athletic should boost passion for Athletics
    # Default passion is 1.0, multiplier 1.5 -> 1.5
    assert skills.states[SkillId.ATHLETICS].passion == 1.5

    # Normal gain 100 * 1.5 = 150
    skill_service.add_xp(e, SkillId.ATHLETICS, 100.0)
    # It levels up (req 100), so 150 - 100 = 50 remaining
    assert skills.states[SkillId.ATHLETICS].current_xp == 50.0
    assert skills.states[SkillId.ATHLETICS].level == 1


def test_decay(world):
    e = world.create_entity()
    skills = Skills()
    # Set up a skill that hasn't been used in a long time
    # Decay starts after 1 day (3600s in our assumption)
    # Let's say it's been 2 days. Decay rate for athletics is 10.0/day (from our skills.toml creation)

    state = SkillState(level=1, current_xp=50.0, last_used_gametime=0.0)
    skills.states[SkillId.ATHLETICS] = state
    world.add_component(e, skills)

    time_service = world.services.get(TimeService)
    # Advance time to 2.5 days (2.5 * 3600 = 9000)
    time_service.time_elapsed = 9000.0

    skill_service = world.services.get(SkillService)
    skill_service.apply_decay(e)

    # Days since use = 2.5
    # Loss = Rate * (2.5 - 1.0) = 10 * 1.5 = 15.0
    # Expected XP = 50 - 15 = 35

    assert math.isclose(state.current_xp, 35.0, abs_tol=0.1)


def test_decay_floor(world):
    e = world.create_entity()
    skills = Skills()

    state = SkillState(level=1, current_xp=5.0, last_used_gametime=0.0)
    skills.states[SkillId.ATHLETICS] = state
    world.add_component(e, skills)

    time_service = world.services.get(TimeService)
    # Advance time a lot
    time_service.time_elapsed = 3600.0 * 10

    skill_service = world.services.get(SkillService)
    skill_service.apply_decay(e)

    # Should floor at 0.0, not go negative
    assert state.current_xp == 0.0
    assert state.level == 1  # No de-leveling


def test_soft_cap(world):
    e = world.create_entity()
    skills = Skills()

    # Soft cap base is 10. Passion 1.0 -> Cap = 10 + 2 = 12.
    # Level 12 should trigger soft cap (0.1 multiplier).

    state = SkillState(level=12, current_xp=0.0, passion=1.0)
    skills.states[SkillId.ATHLETICS] = state
    world.add_component(e, skills)
    world.add_component(e, YukkuriStats(name="Test", type_id="test", discipline=50.0))

    skill_service = world.services.get(SkillService)

    # Gain 100. Effective = 100 * 1.0 * 0.1 = 10
    skill_service.add_xp(e, SkillId.ATHLETICS, 100.0)

    assert math.isclose(state.current_xp, 10.0)


def test_init_no_instant_decay(world):
    time_service = world.services.get(TimeService)
    time_service.time_elapsed = 100000.0  # High time

    e = world.create_entity()
    # No Skills component initially
    world.add_component(e, YukkuriStats(name="Test", type_id="test"))
    world.add_component(e, Personality())

    skill_service = world.services.get(SkillService)
    skill_service.initialize_skills(e)

    skills = world.get_component(e, Skills)
    state = skills.states[SkillId.ATHLETICS]

    # Should start at current time
    assert state.last_used_gametime == 100000.0

    # Apply decay immediately
    skill_service.apply_decay(e)

    # Should be no decay because time diff is 0 (less than 1 day)
    assert state.current_xp == 0.0
