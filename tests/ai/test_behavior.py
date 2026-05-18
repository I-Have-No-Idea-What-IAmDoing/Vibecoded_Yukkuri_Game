import pytest
import pymunk
from py_trees.common import Status
from yukkuri_game.game.ai.navigation_service import PathResult

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.components import Transform, MovementController
from yukkuri_game.game.components import AIState, YukkuriStats, Needs
from yukkuri_game.game.ai.behaviors import MoveToTarget
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
            super().__init__(world_width, world_height, deterministic_mode=True)

        def find_path(self, start, end, can_fly=False):
            return [end]  # Simple straight path

        def request_path(self, entity_id, start, end, capabilities=0, priority=2, timestamp=None):
            path = self.find_path(start, end)
            self.result_queue.put(PathResult(entity_id, path, True))

    world.services.register(MockNavService(1000, 1000), NavigationService)

    return world, entity_id


def test_movetotarget_reaches_target(world_and_entity):
    """Test that the entity successfully reaches the target."""
    world, entity_id = world_and_entity

    ai_state = world.get_component(entity_id, AIState)
    ai_state.state_data = {"target_x": 100, "target_y": 0}

    action = MoveToTarget(entity_id=entity_id, world=world, acceptance_radius=10.0)

    for _ in range(20):  # Increased steps just in case
        status = action.update()
        
        # Simulate NavigationSystem
        nav = world.services.get(NavigationService)
        results = nav.get_results()
        for res in results:
            if res.success:
                ai = world.get_component(res.entity_id, AIState)
                ai.path = res.path

        if status == Status.SUCCESS:
            break

        # Get components needed for simulation
        transform = world.get_component(entity_id, Transform)
        controller = world.get_component(entity_id, MovementController)

        # Simulate SteeringSystem: Process MoveCommand
        from yukkuri_game.game.components import MoveCommand
        if world.has_component(entity_id, MoveCommand):
            cmd = world.get_component(entity_id, MoveCommand)
            # Simple seek behavior for test
            curr_pos = pymunk.Vec2d(transform.x, transform.y)
            # ...
            target_pos = pymunk.Vec2d(cmd.target_pos.x, cmd.target_pos.y)
            direction = (target_pos - curr_pos).normalized()
            controller.target_velocity = direction * (100.0 * cmd.speed_multiplier)
        
        # Manually update transform based on velocity for the test
        transform.x += controller.target_velocity.x * 0.1
        transform.y += controller.target_velocity.y * 0.1

    assert status == Status.SUCCESS
    transform = world.get_component(entity_id, Transform)
    # With 20 steps of 0.1s at 100px/s, it moves 200px (overshoot potential if not careful, but loop breaks on success)
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

    from yukkuri_game.game.components import MoveCommand
    assert world.has_component(entity_id, MoveCommand)
    cmd = world.get_component(entity_id, MoveCommand)
    
    # Speed multiplier should be 0.5 for low energy
    assert cmd.speed_multiplier == pytest.approx(0.5)


def test_movetotarget_falls_back_to_direct_movement_if_no_path(world_and_entity):
    """Test that the action falls back to direct movement if pathfinding fails.

    When the NavigationService returns an empty path, MoveToTarget should
    not fail but instead attempt direct movement towards the target.
    """
    world, entity_id = world_and_entity

    ai_state = world.get_component(entity_id, AIState)
    ai_state.state_data = {"target_x": 100, "target_y": 0}

    # Mock failing navigation service that returns empty path
    class MockFailingNavService(NavigationService):
        def __init__(self, world_width: int, world_height: int):
            super().__init__(world_width, world_height, deterministic_mode=True)

        def find_path(self, start, end, can_fly=False):
            return []
            
        def request_path(self, entity_id, start, end, capabilities=0, priority=2, timestamp=None):
            self.result_queue.put(PathResult(entity_id, [], False))

    world.services.register(
        MockFailingNavService(1000, 1000), NavigationService, replace=True
    )

    action = MoveToTarget(entity_id=entity_id, world=world, speed=100.0)
    status = action.update()

    # Should be RUNNING (attempting direct movement), not FAILURE
    # Should be RUNNING (attempting direct movement), not FAILURE
    assert status == Status.RUNNING
    
    # Process the failed path result
    nav = world.services.get(NavigationService)
    results = nav.get_results()
    for res in results:
        if not res.success:
            ai_state = world.get_component(res.entity_id, AIState)
            ai_state.state_data["path_failed"] = True
            
    # Update again to trigger fallback
    status = action.update()
    assert status == Status.RUNNING
    
    # Check that a MoveCommand was issued (new architecture)
    from yukkuri_game.game.components import MoveCommand
    assert world.has_component(entity_id, MoveCommand)
    
    cmd = world.get_component(entity_id, MoveCommand)
    assert cmd.target_pos.x == 100
