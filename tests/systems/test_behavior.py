"""
Tests for Behavior System.
"""

import unittest
from unittest.mock import MagicMock, patch
import py_trees
from py_trees.common import Status
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.yukkuri_components import AIState


class TestBehaviorSystem(unittest.TestCase):
    def setUp(self):
        # Clear blackboard
        py_trees.blackboard.Blackboard().clear()
        from test_utils import make_configured_world
        self.world = make_configured_world()

    @patch("yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree")
    def test_tree_creation_and_tick(self, mock_create_tree):
        ai = AIState()
        entity = self.world.create_entity()
        self.world.add_component(entity, ai)

        # Mock Tree
        mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
        mock_root.status = Status.RUNNING
        mock_create_tree.return_value = mock_root

        system = BehaviorSystem()
        self.world.add_system(system)

        # Mock the BehaviourTree class to verify ticking
        with patch("py_trees.trees.BehaviourTree") as mock_bt_cls:
            mock_bt = MagicMock()
            # Ensure root has status access
            mock_bt.root = mock_root
            mock_bt_cls.return_value = mock_bt

            # First update might just schedule
            # Update with enough time to trigger tick (0.2s should cover stagger + interval)
            system.update(self.world, 0.2)

            # If staggering delayed it, update again
            system.update(self.world, 0.1)

            mock_create_tree.assert_called()
            self.assertIn(entity, system.trees)

            # Should have ticked at least once
            assert mock_bt.tick.called

    def test_cleanup_destroyed_entities(self) -> None:
        entity = self.world.create_entity()
        self.world.add_component(entity, AIState())

        system = BehaviorSystem()
        self.world.add_system(system)

        # Tick to create tree
        # Need to patch create_tree to return a proper mock with spec
        with patch(
            "yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree"
        ) as mock_create:
            mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
            mock_root.status = Status.RUNNING
            mock_create.return_value = mock_root

            system.update(self.world, 0.1)
            self.assertIn(entity, system.trees)

            # Now destroy entity
            self.world.destroy_entity(entity)

            system.update(self.world, 0.1)
            self.assertNotIn(entity, system.trees)

    def test_blackboard_dt(self) -> None:
        system = BehaviorSystem()
        self.world.add_system(system)

        # We need an entity to trigger the loop where dt is set
        ai = AIState()
        entity = self.world.create_entity()
        self.world.add_component(entity, ai)

        # Patch create_tree
        with (
            patch(
                "yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree"
            ) as mock_create,
            patch("py_trees.trees.BehaviourTree") as mock_bt_cls,
        ):
            mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
            mock_root.status = Status.RUNNING
            mock_create.return_value = mock_root

            mock_bt = MagicMock()
            mock_bt.root = mock_root
            mock_bt_cls.return_value = mock_bt

            # First update to initialize timings (dt won't be set if not ticking)
            system.update(self.world, 0.1)

            # Second update to trigger tick
            # dt passed to update is 0.1
            system.update(self.world, 0.1)

            bb = py_trees.blackboard.Blackboard()
            # dt in blackboard should be approx 0.1 (based on calculated elapsed time)
            # It might not be exactly 0.1 due to floating point or logic
            dt = bb.get("dt")
            self.assertIsNotNone(dt)
            self.assertGreater(dt, 0.0)
            self.assertLess(dt, 1.0)  # Reasonable range
