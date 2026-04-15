from yukkuri_game.engine.types import EntityID

import unittest
import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import AIState, YukkuriStats, Needs
from yukkuri_game.game.components import Transform, InteractionRequest, MovementController
from yukkuri_game.game.ai.behaviors.trees import build_standard_interaction_behavior
from yukkuri_game.game.services import GameService
from py_trees.common import Status

class TestInteractionLogic(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.ai = AIState()
        self.stats = YukkuriStats(type_id="reimu", name="Self")
        self.transform = Transform(x=100, y=100)
        self.entity_id = self.world.create_entity(
            self.ai, self.stats, self.transform, Needs(), MovementController()
        )
        # Mock Check functions
        self.check_goal_true = lambda g: True
        self.check_target_true = lambda: True

    def test_talk_generates_correct_request(self):
        """Test that the 'Talk' behavior generates an InteractionRequest with action='Talk'."""
        
        # 1. Setup Target (Friend)
        friend_id = EntityID(self.world.create_entity(
            YukkuriStats(type_id="reimu", name="Friend"),
            Transform(x=120, y=100) # 20px away (within interaction range)
        ))
        if self.ai: self.ai.current_target_id = friend_id
        
        # 2. Build Behavior Tree for "Talk"
        builder = build_standard_interaction_behavior("Talk")
        behavior_tree = builder(
            self.entity_id, 
            self.world, 
            1000, 1000, 
            self.check_goal_true,
            self.check_target_true
        )

        # 3. Tick Tree
        # We expect it to traverse: Check Goal -> Selector -> MoveTo (Success/Skipped) -> Interact
        behavior_tree.tick_once()

        # 4. Check for InteractionRequest
        request = self.world.try_get_component(self.entity_id, InteractionRequest)
        
        self.assertIsNotNone(request, "Talk behavior should generate an InteractionRequest")
        self.assertEqual(request.action, "Talk", f"Expected action='Talk', got '{request.action}'")

if __name__ == "__main__":
    unittest.main()
