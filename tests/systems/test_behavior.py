import unittest
from unittest.mock import MagicMock, patch
import py_trees
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.yukkuri_components import AIState

class TestBehaviorSystem(unittest.TestCase):
    @patch('yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree')
    def test_tree_creation_and_tick(self, mock_create_tree):
        mock_world = MagicMock()
        ai = AIState()
        mock_world.get_components_tuple.return_value = [(1, (ai,))]
        mock_world.get_entities_with.return_value = [1] # For cleanup check

        # Mock Tree
        mock_root = MagicMock(spec=py_trees.behaviour.Behaviour)
        mock_create_tree.return_value = mock_root

        system = BehaviorSystem(100, 100)

        # Mock the BehaviourTree class to verify ticking
        with patch('py_trees.trees.BehaviourTree') as mock_bt_cls:
            mock_bt = MagicMock()
            mock_bt_cls.return_value = mock_bt

            # First update: Should create tree and tick
            system.update(mock_world, 0.1)

            mock_create_tree.assert_called_once_with(1, mock_world, 100, 100)
            self.assertIn(1, system.trees)
            # mock_bt.tick.assert_called_once() # This might be called on the wrapper if it exists or the mock return value
            # Since we wrap root in BehaviourTree(root), and BehaviourTree(root).tick() is called.
            # The mock_bt_cls returns mock_bt.
            mock_bt.tick.assert_called_once()

            # Second update: Should NOT create tree, just tick
            system.update(mock_world, 0.1)
            mock_create_tree.assert_called_once() # Count remains 1
            self.assertEqual(mock_bt.tick.call_count, 2)

    def test_blackboard_dt(self):
        mock_world = MagicMock()
        mock_world.get_components_tuple.return_value = []

        system = BehaviorSystem(100, 100)
        system.update(mock_world, 0.5)

        bb = py_trees.blackboard.Blackboard()
        self.assertEqual(bb.get("dt"), 0.5)
