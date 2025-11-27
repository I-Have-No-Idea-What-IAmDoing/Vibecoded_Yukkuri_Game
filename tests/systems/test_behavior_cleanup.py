import unittest
from unittest.mock import MagicMock, patch
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import AIState
import py_trees

class TestBehaviorSystemCleanup(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.system = BehaviorSystem(100.0, 100.0)

        # Need to mock create_yukkuri_behavior_tree because it depends on other components/systems
        # and we only want to test the system logic, not the tree construction itself
        self.patcher = patch('yukkuri_game.game.systems.behavior.create_yukkuri_behavior_tree')
        self.mock_create_tree = self.patcher.start()

        # Return a dummy behavior tree root
        self.mock_create_tree.return_value = py_trees.composites.Sequence(name="Root", memory=True)

    def tearDown(self):
        self.patcher.stop()

    def test_behavior_cleanup(self):
        # Create an entity with AIState
        entity_id = self.world.create_entity()
        self.world.add_component(entity_id, AIState())

        # Run update - should create a tree
        self.system.update(self.world, 0.1)

        self.assertIn(entity_id, self.system.trees)
        self.assertIsInstance(self.system.trees[entity_id], py_trees.trees.BehaviourTree)

        # Destroy the entity
        self.world.destroy_entity(entity_id)

        # Verify entity is gone (sanity check)
        self.assertFalse(self.world.entity_exists(entity_id))

        # Run update again - should clean up the tree
        self.system.update(self.world, 0.1)

        self.assertNotIn(entity_id, self.system.trees)

if __name__ == '__main__':
    unittest.main()
