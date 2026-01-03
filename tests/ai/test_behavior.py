import pytest
import pymunk
from py_trees.common import Status

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, MovementController
from yukkuri_game.game.yukkuri_components import AIState, YukkuriStats, Needs
from yukkuri_game.game.ai.behavior import MoveToTarget
from yukkuri_game.game.ai.navigation_service import NavigationService


@pytest.fixture
def world_and_entity():
    """Sets up a world with a single entity for AI tests."""
    world = World()
    entity_id = world.create_entity()

    world.add_component(entity_id, Transform(x=0, y=0))
    world.add_component(entity_id, MovementController())
    world.add_component(entity_id, AIState())
    world.add_component(entity_id, YukkuriStats(name="test_yukkuri", type_id="reimu"))
    world.add_component(entity_id, Needs(energy=100.0))

    # Mock navigation service
    class MockNavService(NavigationService):
        def __init__(self, world_width: int, world_height: int):
            pass

        def find_path(self, start, end):
            return [end]  # Simple straight path

    world.services.register(MockNavService(1000, 1000), NavigationService)

    return world, entity_id


def test_movetotarget_reaches_target(world_and_entity):
    """Test that the entity successfully reaches the target."""
    world, entity_id = world_and_entity

    ai_state = world.get_component(entity_id, AIState)
    ai_state.state_data = {"target_x": 100, "target_y": 0}

    action = MoveToTarget(entity_id=entity_id, world=world)

    # Simulate a few steps
    for _ in range(10):
        status = action.update()
        if status == Status.SUCCESS:
            break

        # Manually update transform based on velocity for the test
        controller = world.get_component(entity_id, MovementController)
        transform = world.get_component(entity_id, Transform)
        transform.x += controller.target_velocity.x * 0.1
        transform.y += controller.target_velocity.y * 0.1

    assert status == Status.SUCCESS
    transform = world.get_component(entity_id, Transform)
    assert transform.x == pytest.approx(100, abs=15)


def test_movetotarget_stops_when_done(world_and_entity):
    """Test that the entity's target velocity is zeroed out upon success."""
    world, entity_id = world_and_entity

    ai_state = world.get_component(entity_id, AIState)
    transform = world.get_component(entity_id, Transform)
    transform.x, transform.y = 95, 0  # Start close to the target
    ai_state.state_data = {"target_x": 100, "target_y": 0}

    action = MoveToTarget(entity_id=entity_id, world=world)
    status = action.update()

    assert status == Status.SUCCESS
    controller = world.get_component(entity_id, MovementController)
    assert controller.target_velocity == pymunk.Vec2d(0, 0)


def test_movetotarget_slows_down_when_low_energy(world_and_entity):
    """Test that the entity moves slower when its energy is low."""
    world, entity_id = world_and_entity

    ai_state = world.get_component(entity_id, AIState)
    ai_state.state_data = {"target_x": 100, "target_y": 0}
    needs = world.get_component(entity_id, Needs)
    needs.energy = 20  # Low energy

    action = MoveToTarget(entity_id=entity_id, world=world, speed=100.0)
    action.update()

    controller = world.get_component(entity_id, MovementController)
    # Speed should be halved (100 * 0.5)
    assert controller.target_velocity.length == pytest.approx(50.0)


def test_movetotarget_fails_gracefully_if_no_path(world_and_entity):
    """Test that the action fails if the navigation service can't find a path."""
    world, entity_id = world_and_entity

    ai_state = world.get_component(entity_id, AIState)
    ai_state.state_data = {"target_x": 100, "target_y": 0}

    # Mock failing navigation service
    class MockFailingNavService(NavigationService):
        def __init__(self, world_width: int, world_height: int):
            pass

        def find_path(self, start, end):
            return []

    world.services.register(
        MockFailingNavService(1000, 1000), NavigationService, replace=True
    )

    action = MoveToTarget(entity_id=entity_id, world=world)
    status = action.update()

    assert status == Status.FAILURE
    controller = world.get_component(entity_id, MovementController)
    assert controller.target_velocity == pymunk.Vec2d(0, 0)
