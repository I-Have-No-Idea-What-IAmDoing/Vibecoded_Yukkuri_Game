
import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import TraitService
from yukkuri_game.game.ai.utility import UtilityAIEngine, Action, Consideration
from yukkuri_game.game.yukkuri_components import Personality
from yukkuri_game.engine.resource_manager import ResourceManager

class MockResourceManager:
    def __init__(self):
        self.ai_actions = {}

class TestAITraits(unittest.TestCase):
    def test_trait_overrides(self):
        world = World()

        # We assume data dir exists. If not, this test might fail in environment without data.
        # But strictly we should mock TraitService loading.
        # For this verification script, we use real TraitService with real data.
        if not os.path.exists("data"):
            self.skipTest("Data directory not found")

        trait_service = TraitService(data_dir="data")

        # Setup Engine
        rm = MockResourceManager()
        engine = UtilityAIEngine(rm)
        engine.set_trait_service(trait_service)

        # Manually add the action "Social/Empathy" to engine
        # Normal curve: linear, m=1.0
        cons = Consideration(
            name="Social/Empathy",
            input_key="input_val",
            curve_type="linear",
            params={"m": 1.0}
        )
        action = Action(
            name="BeNice",
            considerations=[cons],
            weight=1.0
        )
        engine.actions["BeNice"] = action

        # Test Case 1: Normal Personality
        p_normal = Personality()
        context_normal = {
            "input_val": 100.0, # Should give score 1.0 normally
            "__personality__": p_normal
        }

        overrides_normal = trait_service.get_effective_modifiers(p_normal)
        score_normal = action.calculate_utility(context_normal, overrides_normal)

        self.assertAlmostEqual(score_normal, 1.0, places=2, msg="Normal score should be 1.0")

        # Test Case 2: Gesu Personality
        p_gesu = Personality()
        p_gesu.traits.add("GESU")
        context_gesu = {
            "input_val": 100.0,
            "__personality__": p_gesu
        }

        overrides_gesu = trait_service.get_effective_modifiers(p_gesu)
        score_gesu = action.calculate_utility(context_gesu, overrides_gesu)

        # Gesu trait overrides "Social/Empathy" with m=-1.0 -> score 0.0
        self.assertAlmostEqual(score_gesu, 0.0, places=2, msg="Gesu score should be 0.0")

if __name__ == "__main__":
    unittest.main()
