import pytest
from test_utils import make_configured_world
from unittest.mock import MagicMock
from yukkuri_game.game.systems.lifecycle import LifecycleSystem
from yukkuri_game.game.components import YukkuriStats, Needs
from yukkuri_game.config import LifecycleSettings
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.entity_factory import EntityFactory


# Mock ResourceManager data structure
class MockResourceManager:
    def __init__(self):
        self.yukkuri_types = {
            "reimu": {
                "name": "Reimu",
                "image": "reimu.png",
                "max_health": 100,
                "width": 64,
                "height": 64,
            }
        }
        self.item_types = {}

        # Mock tuning
        self.tuning = MagicMock()
        self.tuning.visuals.movement.bob_height = 10.0
        self.tuning.visuals.movement.bob_speed = 5.0


@pytest.fixture
def resource_manager():
    return MockResourceManager()


@pytest.fixture
def world(resource_manager):
    w = make_configured_world()
    # Register MockResourceManager as the ResourceManager service
    # We need to import the actual ResourceManager type for the key
    from yukkuri_game.engine.resource_manager import ResourceManager

    w.services.register(resource_manager, ResourceManager)
    return w


@pytest.fixture
def entity_factory(world):
    return EntityFactory(world)


@pytest.fixture
def lifecycle_system(entity_factory, world):
    from yukkuri_game.config import GameConfig

    config = world.services.get(GameConfig)
    # The system will use world.add_system -> initialize() -> fetch from config
    # We can override the config settings here if needed
    config.rules.lifecycle.baby_age_threshold = 100.0
    config.rules.lifecycle.child_age_threshold = 300.0

    system = LifecycleSystem()
    world.add_system(system)
    return system


def test_growth_max_health_inconsistency(lifecycle_system, entity_factory, world):
    """
    Verifies that a Yukkuri grown from a baby has the same max health
    as a Yukkuri spawned directly as an adult.
    """
    # 1. Spawn a Baby
    baby_id = entity_factory.create_yukkuri("reimu", 0, 0, age=0)
    baby_stats = world.get_component(baby_id, YukkuriStats)
    baby_needs = world.get_component(baby_id, Needs)

    # Verify initial baby stats (should be half of base 100)
    assert baby_stats.growth_stage == "Baby"
    assert baby_needs.max_health == 50.0

    # 2. Grow Baby to Child
    baby_stats.age = 150  # Above child threshold
    lifecycle_system.update(world, 1.0)  # Trigger growth

    # Verify child stats
    assert baby_stats.growth_stage == "Child"
    # Lifecycle system adds 50 to max_health
    assert baby_needs.max_health == 100.0

    # 3. Grow Child to Adult
    baby_stats.age = 350  # Above adult threshold
    lifecycle_system.update(world, 1.0)  # Trigger growth

    # Verify grown adult stats
    assert baby_stats.growth_stage == "Adult"
    # Lifecycle system adds another 50 to max_health? (Wait, Lifecycle logic adds 50 for child, maybe different for adult?)
    # Looking at lifecycle.py:
    # if new_stage == "Child": stats.max_health += 50
    # It doesn't seem to add for Adult.

    grown_adult_max_health = baby_needs.max_health
    print(f"Grown Adult Max Health: {grown_adult_max_health}")

    # 4. Spawn an Adult directly
    adult_id = entity_factory.create_yukkuri("reimu", 100, 100, age=350)
    adult_stats = world.get_component(adult_id, YukkuriStats)
    adult_needs = world.get_component(adult_id, Needs)

    # Verify spawned adult stats
    assert adult_stats.growth_stage == "Adult"
    spawned_adult_max_health = adult_needs.max_health
    print(f"Spawned Adult Max Health: {spawned_adult_max_health}")

    # 5. Assert Consistency
    assert grown_adult_max_health == spawned_adult_max_health, (
        f"Inconsistency detected! Grown: {grown_adult_max_health}, Spawned: {spawned_adult_max_health}"
    )
