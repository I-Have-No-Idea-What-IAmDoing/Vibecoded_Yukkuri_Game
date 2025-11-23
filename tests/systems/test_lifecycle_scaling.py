
import pytest
from unittest.mock import MagicMock
from src.yukkuri_game.game.systems.lifecycle import LifecycleSystem
from src.yukkuri_game.game.yukkuri_components import YukkuriStats
from src.yukkuri_game.game.components import Transform
from src.yukkuri_game.engine.ecs import World

def test_lifecycle_scaling_correctness():
    """
    Test that scale is correctly updated relative to the current scale during growth.
    """
    # Setup
    world = World()
    settings = MagicMock()
    factory = MagicMock()
    system = LifecycleSystem(settings, factory)

    entity = world.create_entity()
    # Correct initialization for a Baby is scale 0.5 (verified in EntityFactory)
    stats = YukkuriStats(name="Test", type_id="test", max_health=100, health=100, age=0, growth_stage="Baby")
    transform = Transform(x=0, y=0, scale=0.5)

    world.add_component(entity, stats)
    world.add_component(entity, transform)

    # 1. Baby -> Child
    # Multiplier: 1.5
    # Expected: 0.5 * 1.5 = 0.75
    system._grow_entity(world, entity, stats, transform, "Child", 1.5)

    assert stats.growth_stage == "Child"
    assert transform.scale == 0.75

    # 2. Child -> Adult
    # Multiplier: 4.0/3.0
    # Expected: 0.75 * (4/3) = 1.0
    system._grow_entity(world, entity, stats, transform, "Adult", 4.0/3.0)

    assert stats.growth_stage == "Adult"
    assert transform.scale == 1.0

def test_lifecycle_scaling_incorrect_initialization():
    """
    Test how scaling behaves if initialized incorrectly (regression risk check).
    If initialization is wrong (e.g. Baby at 1.0), it will propagate.
    This test documents the expected behavior of the new implementation.
    """
    world = World()
    settings = MagicMock()
    factory = MagicMock()
    system = LifecycleSystem(settings, factory)

    entity = world.create_entity()
    # Incorrect initialization: Baby at scale 1.0
    stats = YukkuriStats(name="Test", type_id="test", max_health=100, health=100, age=0, growth_stage="Baby")
    transform = Transform(x=0, y=0, scale=1.0)

    world.add_component(entity, stats)
    world.add_component(entity, transform)

    # Baby -> Child (x1.5)
    system._grow_entity(world, entity, stats, transform, "Child", 1.5)
    assert transform.scale == 1.5 # Propagated error, which is expected behavior for relative scaling.

    # Child -> Adult (x1.33)
    system._grow_entity(world, entity, stats, transform, "Adult", 4.0/3.0)
    assert transform.scale == 2.0 # Propagated error.
