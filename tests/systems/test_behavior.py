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

    @patch("yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree")
    def test_tree_creation_and_tick(self, mock_create_tree):
        mock_world = MagicMock()
        ai = AIState()
        mock_world.get_components_tuple.return_value = [(1, (ai,))]
        mock_world.get_entities_with.return_value = [1]  # For cleanup check

        # Mock Tree
        mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
        mock_root.status = Status.RUNNING
        mock_create_tree.return_value = mock_root

        system = BehaviorSystem(100, 100)

        # Mock the BehaviourTree class to verify ticking
        with patch("py_trees.trees.BehaviourTree") as mock_bt_cls:
            mock_bt = MagicMock()
            # Ensure root has status access
            mock_bt.root = mock_root
            mock_bt_cls.return_value = mock_bt

            # First update might just schedule
            # Update with enough time to trigger tick (0.2s should cover stagger + interval)
            system.update(mock_world, 0.2)

            # If staggering delayed it, update again
            system.update(mock_world, 0.1)

            mock_create_tree.assert_called_once_with(1, mock_world, 100, 100)
            self.assertIn(1, system.trees)

            # Should have ticked at least once
            assert mock_bt.tick.called

    def test_cleanup_destroyed_entities(self):
        mock_world = MagicMock()

        # Initial: Entity 1 exists
        mock_world.get_components_tuple.return_value = [(1, (AIState(),))]
        # Entity 1 exists check
        def entity_exists(eid):
            return eid == 1
        mock_world.entity_exists.side_effect = entity_exists
        mock_world.has_component.return_value = True

        system = BehaviorSystem(100, 100)

        # Tick to create tree
        # Need to patch create_tree to return a proper mock with spec
        with patch("yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree") as mock_create:
             mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
             mock_root.status = Status.RUNNING
             mock_create.return_value = mock_root

             system.update(mock_world, 0.1)
             self.assertIn(1, system.trees)

             # Now destroy entity 1
             mock_world.entity_exists.side_effect = lambda eid: False

             # Need to ensure get_components_tuple returns empty or we just rely on cleanup loop
             # Cleanup loop iterates system.trees.keys()

             system.update(mock_world, 0.1)
             self.assertNotIn(1, system.trees)

    def test_blackboard_dt(self):
        mock_world = MagicMock()
        mock_world.get_components_tuple.return_value = []

        system = BehaviorSystem(100, 100)

        # We need an entity to trigger the loop where dt is set
        ai = AIState()
        mock_world.get_components_tuple.return_value = [(1, (ai,))]

        # Patch create_tree
        with patch("yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree") as mock_create, \
             patch("py_trees.trees.BehaviourTree") as mock_bt_cls:

            mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
            mock_root.status = Status.RUNNING
            mock_create.return_value = mock_root

            mock_bt = MagicMock()
            mock_bt.root = mock_root
            mock_bt_cls.return_value = mock_bt

            # First update to initialize timings (dt won't be set if not ticking)
            system.update(mock_world, 0.1)

            # Second update to trigger tick
            # dt passed to update is 0.1
            system.update(mock_world, 0.1)

            bb = py_trees.blackboard.Blackboard()
            # dt in blackboard should be approx 0.1 (based on calculated elapsed time)
            # It might not be exactly 0.1 due to floating point or logic
            dt = bb.get("dt")
            self.assertIsNotNone(dt)
            self.assertGreater(dt, 0.0)
            self.assertLess(dt, 1.0) # Reasonable range
