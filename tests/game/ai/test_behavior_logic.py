import pytest
from unittest.mock import MagicMock, patch
import py_trees
from py_trees.common import Status
from yukkuri_game.game.ai.behavior import (
    MoveToTarget, Wander, Interact, Idle, Check, FindItem,
    build_eat_behavior, build_sleep_behavior, build_play_behavior,
    build_wander_behavior, build_talk_behavior, build_fight_behavior,
    build_dance_behavior, create_yukkuri_behavior_tree
)
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, PhysicsBody, InteractionRequest, MovementController
from yukkuri_game.game.yukkuri_components import AIState, YukkuriStats, ItemStats
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.game.services import GameService

class TestMoveToTarget:
    @pytest.fixture
    def mock_world(self):
        return MagicMock(spec=World)

    @pytest.fixture
    def mock_blackboard(self):
        return MagicMock()

    def test_move_no_target(self, mock_world, mock_blackboard):
        action = MoveToTarget(entity_id=1, world=mock_world, blackboard=mock_blackboard)

        mock_world.get_component.side_effect = lambda e, c: None

        assert action.update() == Status.FAILURE

    def test_move_reached_target(self, mock_world, mock_blackboard):
        action = MoveToTarget(entity_id=1, world=mock_world, blackboard=mock_blackboard)

        ai = MagicMock(current_target_id=2, path=[(100, 100)], state_data={})
        trans = MagicMock(x=99, y=99) # Close to target
        stats = MagicMock() # YukkuriStats
        controller = MagicMock() # MovementController

        def get_component(e, c):
            if e == 1:
                if c == AIState: return ai
                if c == Transform: return trans
                if c == YukkuriStats: return stats
                if c == MovementController: return controller
            if e == 2:
                if c == Transform: return MagicMock(x=100, y=100)
            return None

        mock_world.get_component.side_effect = get_component

        # Mock blackboard for dt
        with patch('py_trees.blackboard.Blackboard') as mock_bb:
            mock_bb.return_value.get.return_value = 0.1
            status = action.update()

        assert status == Status.SUCCESS

    def test_move_pathfinding_needed(self, mock_world, mock_blackboard):
        action = MoveToTarget(entity_id=1, world=mock_world, blackboard=mock_blackboard)

        ai = MagicMock(current_target_id=2, path=None, state_data={})
        trans = MagicMock(x=0, y=0)
        stats = MagicMock(energy=100) # Ensure energy comparison works
        controller = MagicMock()

        nav_service = MagicMock(spec=NavigationService)
        nav_service.find_path.return_value = [(50, 50), (100, 100)]
        mock_world.services = MagicMock()
        mock_world.services.try_get.return_value = nav_service

        def get_component(e, c):
            if e == 1:
                if c == AIState: return ai
                if c == Transform: return trans
                if c == YukkuriStats: return stats
                if c == MovementController: return controller
            if e == 2:
                if c == Transform: return MagicMock(x=100, y=100)
            return None

        mock_world.get_component.side_effect = get_component

        with patch('py_trees.blackboard.Blackboard') as mock_bb:
            mock_bb.return_value.get.return_value = 0.1
            status = action.update()

        assert status == Status.RUNNING
        assert ai.path == [(50, 50), (100, 100)]
        nav_service.find_path.assert_called_once()

class TestInteract:
    def test_interact_success(self):
        world = MagicMock(spec=World)
        action = Interact(entity_id=1, world=world)

        ai = MagicMock(current_target_id=2)
        trans = MagicMock(x=10, y=10)
        target_trans = MagicMock(x=15, y=15) # Close enough

        def get_component(e, c):
            if e == 1:
                if c == AIState: return ai
                if c == Transform: return trans
            if e == 2:
                if c == Transform: return target_trans
            return None

        world.get_component.side_effect = get_component
        world.has_component.return_value = False # No existing interaction request

        status = action.update()
        assert status == Status.SUCCESS
        world.add_component.assert_called()

    def test_interact_too_far(self):
        world = MagicMock(spec=World)
        action = Interact(entity_id=1, world=world)

        ai = MagicMock(current_target_id=2)
        trans = MagicMock(x=10, y=10)
        target_trans = MagicMock(x=100, y=100) # Too far

        def get_component(e, c):
            if e == 1:
                if c == AIState: return ai
                if c == Transform: return trans
            if e == 2:
                if c == Transform: return target_trans
            return None

        world.get_component.side_effect = get_component

        status = action.update()
        assert status == Status.RUNNING

class TestBehaviorBuilders:
    @pytest.fixture
    def mock_args(self):
        return {
            "entity_id": 1,
            "world": MagicMock(spec=World),
            "width": 1000,
            "height": 1000,
            "check_goal_fn": MagicMock(return_value=True),
            "check_target_fn": MagicMock(return_value=True)
        }

    def test_build_eat_behavior(self, mock_args):
        behavior = build_eat_behavior(**mock_args)
        assert isinstance(behavior, py_trees.composites.Sequence)
        assert behavior.name == "Eat Sequence"

    def test_build_sleep_behavior(self, mock_args):
        behavior = build_sleep_behavior(**mock_args)
        assert isinstance(behavior, py_trees.composites.Sequence)

    def test_build_play_behavior(self, mock_args):
        behavior = build_play_behavior(**mock_args)
        assert isinstance(behavior, py_trees.composites.Sequence)

    def test_build_wander_behavior(self, mock_args):
        behavior = build_wander_behavior(**mock_args)
        assert isinstance(behavior, py_trees.composites.Sequence)

    def test_create_yukkuri_behavior_tree(self, mock_args):
        tree = create_yukkuri_behavior_tree(1, mock_args["world"], 1000, 1000)
        # Verify root is a Selector (due to Stress Break update)
        assert isinstance(tree, py_trees.composites.Selector)

        # Structure: Root Selector -> Stress Break Sequence -> Normal Behavior Sequence
        assert len(tree.children) == 2

        stress_break = tree.children[0]
        assert isinstance(stress_break, py_trees.composites.Sequence)
        assert stress_break.name == "Stress Break"

        normal_behavior = tree.children[1]
        assert isinstance(normal_behavior, py_trees.composites.Sequence)
        assert normal_behavior.name == "Normal Behavior"

        # Verify Normal Behavior structure
        assert len(normal_behavior.children) == 2
        # Child 0: Utility Selector
        assert isinstance(normal_behavior.children[0], py_trees.behaviour.Behaviour)
        # Child 1: Execution Selector
        assert isinstance(normal_behavior.children[1], py_trees.composites.Selector)

class TestFindItem:
    def test_find_item_success(self):
        world = MagicMock(spec=World)
        action = FindItem(name="Find", entity_id=1, world=world, stat_criteria="nutrition")

        ai = MagicMock()
        trans = MagicMock(x=0, y=0)

        def get_component(e, c):
            if e == 1:
                if c == AIState: return ai
                if c == Transform: return trans
            return None

        world.get_component.side_effect = get_component

        game_service = MagicMock(spec=GameService)
        game_service.find_best_item.return_value = 2
        world.services = MagicMock()
        world.services.try_get.return_value = game_service

        status = action.update()

        assert status == Status.SUCCESS
        assert ai.current_target_id == 2
        assert ai.path is None

    def test_find_item_failure(self):
        world = MagicMock(spec=World)
        action = FindItem(name="Find", entity_id=1, world=world, stat_criteria="nutrition")

        ai = MagicMock()
        trans = MagicMock(x=0, y=0)

        def get_component(e, c):
            if e == 1:
                if c == AIState: return ai
                if c == Transform: return trans
            return None

        world.get_component.side_effect = get_component

        game_service = MagicMock(spec=GameService)
        game_service.find_best_item.return_value = -1
        world.services = MagicMock()
        world.services.try_get.return_value = game_service

        status = action.update()

        assert status == Status.FAILURE
