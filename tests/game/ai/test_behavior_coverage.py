import pytest
from unittest.mock import MagicMock, patch
import math
from py_trees.common import Status
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.ai.behavior import MoveToTarget, Wander, Interact, Idle, FindItem
from src.yukkuri_game.game.yukkuri_components import AIState, ItemStats, YukkuriStats
from src.yukkuri_game.game.components import Transform, PhysicsBody
from src.yukkuri_game.game.ai.navigation_service import NavigationService
from src.yukkuri_game.game.services import GameService

def test_move_to_target_stuck_detection():
    world = World()
    nav_service = MagicMock(spec=NavigationService)
    world.services.register(nav_service)
    # Ensure try_get returns navigation service
    world.services.try_get = MagicMock(side_effect=lambda t: nav_service if t == NavigationService else None)

    entity = world.create_entity()
    ai = AIState()
    trans = Transform(x=0, y=0)
    phys = MagicMock(spec=PhysicsBody) # Assuming PhysicsBody object logic, but mocked here.
    # Wait, PhysicsBody usually has a .body attribute.
    phys.body = MagicMock()

    world.add_component(entity, ai)
    world.add_component(entity, trans)
    world.add_component(entity, phys)

    # Set target
    ai.state_data = {"target_x": 100.0, "target_y": 0.0}

    # Mock navigation to return a path
    nav_service.find_path.return_value = [(50.0, 0.0), (100.0, 0.0)]

    action = MoveToTarget(entity_id=entity, world=world)

    # First update sets up path and last_position
    with patch('py_trees.blackboard.Blackboard') as mock_bb:
        mock_bb.return_value.get.return_value = 1.0 # dt = 1.0
        status = action.update()
        assert status == Status.RUNNING
        assert ai.path is not None

    # Now simulate NOT moving (stuck)
    # last_position should be set to (0,0) from previous update.
    # Call update again with same transform position.

    with patch('py_trees.blackboard.Blackboard') as mock_bb:
        mock_bb.return_value.get.return_value = 1.0

        # First stuck tick. dt=1.0. stuck_timer becomes 1.0. Threshold is > 1.0.
        # So we need one more tick.
        action.update()

        # Trigger stuck logic (stuck_timer > 1.0)
        action.update()

        # Should be stuck now
        # When stuck, it clears path and applies impulse
        # But if path is cleared, next update will trigger repathing (RUNNING) or FAILURE if no path found
        # But here we check if apply_impulse was called

        assert phys.body.apply_impulse_at_local_point.called

def test_move_to_target_success():
    world = World()
    nav_service = MagicMock(spec=NavigationService)
    world.services.register(nav_service)

    entity = world.create_entity()
    ai = AIState()
    trans = Transform(x=95, y=0) # Close to target

    world.add_component(entity, ai)
    world.add_component(entity, trans)

    ai.state_data = {"target_x": 100.0, "target_y": 0.0}

    action = MoveToTarget(entity_id=entity, world=world)

    with patch('py_trees.blackboard.Blackboard') as mock_bb:
        mock_bb.return_value.get.return_value = 0.1

        # Close enough to not need pathfinding
        status = action.update()
        assert status == Status.SUCCESS

def test_interact_fallback():
    # Test Interact logic when GameService is missing (fallback logic)
    world = World()

    e1 = world.create_entity() # Yukkuri
    ai = AIState(current_target_id=-1)
    trans1 = Transform(x=0, y=0)
    stats = YukkuriStats(name="T", type_id="t", hunger=50.0)

    world.add_component(e1, ai)
    world.add_component(e1, trans1)
    world.add_component(e1, stats)

    e2 = world.create_entity() # Item
    trans2 = Transform(x=10, y=0) # Close
    item_stats = ItemStats(name="Food", type_id="food", cost=10, nutrition=20.0)

    world.add_component(e2, trans2)
    world.add_component(e2, item_stats)

    ai.current_target_id = e2

    action = Interact(entity_id=e1, world=world, consume=True)

    status = action.update()
    assert status == Status.SUCCESS

    # Verify effects
    assert stats.hunger == 30.0 # 50 - 20
    assert not world.entity_exists(e2) # Consumed

def test_find_item():
    world = World()
    game_service = MagicMock(spec=GameService)
    world.services.register(game_service)
    # Need to ensure try_get returns mock
    world.services.try_get = MagicMock(return_value=game_service)

    entity = world.create_entity()
    world.add_component(entity, AIState())
    world.add_component(entity, Transform(x=0, y=0))

    # Mock find_best_item
    game_service.find_best_item.return_value = 999

    action = FindItem(name="Find", entity_id=entity, world=world, stat_criteria="nutrition")

    status = action.update()

    assert status == Status.SUCCESS
    ai = world.get_component(entity, AIState)
    assert ai.current_target_id == 999
