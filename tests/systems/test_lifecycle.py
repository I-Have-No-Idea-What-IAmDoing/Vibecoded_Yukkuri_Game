import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.game.systems.lifecycle import LifecycleSystem
from yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, Dead, EmotionalState
from yukkuri_game.game.components import Sprite, Transform
from yukkuri_game.config import LifecycleSettings
from yukkuri_game.engine.ecs import World

@pytest.fixture
def lifecycle_system():
    settings = LifecycleSettings(
        baby_age_threshold=100.0,
        child_age_threshold=300.0,
        breeding_happiness_threshold=80.0,
        breeding_energy_threshold=80.0,
        breeding_chance=1.0 # 100% chance for testing
    )
    return LifecycleSystem(settings)

@pytest.fixture
def world():
    return World()

def test_handle_death(lifecycle_system, world):
    # Setup
    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="test", health=-10, max_health=100)
    world.add_component(entity, stats)
    world.add_component(entity, AIState())
    world.add_component(entity, Sprite(image_name="test.png", width=64, height=64))

    # Run
    lifecycle_system.update(world, 0.1)

    # Verify
    assert world.has_component(entity, Dead)
    assert not world.has_component(entity, AIState)
    assert stats.health == 0
    sprite = world.get_component(entity, Sprite)
    # assert sprite.rotation == 180.0 # Rotation not supported on Sprite component yet
    assert sprite.flip_y is True

def test_handle_growth(lifecycle_system, world):
    # Setup Baby -> Child
    entity = world.create_entity()
    stats = YukkuriStats(name="Baby", type_id="test", age=150, growth_stage="Baby", health=50, max_health=100)
    transform = Transform(x=0, y=0, scale=0.5)
    world.add_component(entity, stats)
    world.add_component(entity, transform)

    # Run
    lifecycle_system.update(world, 0.1)

    # Verify
    assert stats.growth_stage == "Child"
    assert transform.scale == 0.75
    assert stats.max_health == 150
    assert stats.health == 100

@patch('yukkuri_game.game.systems.lifecycle.create_yukkuri')
def test_handle_breeding(mock_create_yukkuri, lifecycle_system, world):
    # Setup Adult
    entity = world.create_entity()
    stats = YukkuriStats(
        name="Parent",
        type_id="reimu",
        age=600,
        growth_stage="Adult",
        energy=90
    )
    emotional = EmotionalState(happiness=90.0)

    transform = Transform(x=100, y=100)
    world.add_component(entity, stats)
    world.add_component(entity, emotional)
    world.add_component(entity, transform)

    # Run
    lifecycle_system.update(world, 0.1)

    # Verify
    assert stats.energy == 90 - lifecycle_system.settings.breeding_cost
    mock_create_yukkuri.assert_called_once()

    # Check arguments
    # create_yukkuri(world, type_id=..., x=..., y=..., age=..., parents=...)
    # We check keyword args if used, or positional
    call_kwargs = mock_create_yukkuri.call_args.kwargs
    if not call_kwargs:
        # Fallback to positional if kwargs not used by call
        args = mock_create_yukkuri.call_args.args
        # args[0] is world
        assert args[1] == "reimu" # type_id
        assert abs(args[2] - 100) <= 20 # x
        assert abs(args[3] - 100) <= 20 # y
        assert args[4] == 0.0 # age
    else:
        assert call_kwargs['type_id'] == "reimu"
        assert call_kwargs['age'] == 0.0
        assert abs(call_kwargs['x'] - 100) <= 20
        assert abs(call_kwargs['y'] - 100) <= 20
