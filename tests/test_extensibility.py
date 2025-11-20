import unittest
import os
from src.utils.loader import game_data
from src.engine.utility_ai import UtilityAI
from src.engine.ecs import Entity, EntityManager
from src.engine.components import Stats, AIComponent, Identity

class TestGameExtensibility(unittest.TestCase):
    def setUp(self):
        # Load data
        game_data.load_all()
        self.ai = UtilityAI()
        self.ecs = EntityManager()

    def test_yukkuri_creation(self):
        """Verify Yukkuri types are loaded and can be instantiated."""
        types = game_data.yukkuri_types
        self.assertIn("marisa", types)
        self.assertIn("reimu", types)
        self.assertIn("alice", types)

        # Check attributes
        marisa = types["marisa"]
        self.assertEqual(marisa["base_health"], 100)

    def test_ai_evaluation(self):
        """Verify AI evaluates actions correctly based on stats."""
        e = Entity()
        stats = Stats(hunger=90, max_hunger=100) # Very hungry
        e.add_component(stats)

        # Check available actions
        actions = game_data.ai_actions
        self.assertIn("eat", actions)

        # Score actions
        # We need a fake entities list for context (e.g. food availability)
        entities = [] # No food available

        score_no_food = self.ai.score_action("eat", actions["eat"], e, entities)

        # Add food
        from src.engine.components import ItemComponent
        food = Entity()
        food.add_component(ItemComponent(item_type="food"))
        entities.append(food)

        score_with_food = self.ai.score_action("eat", actions["eat"], e, entities)

        # Score should be higher with food
        self.assertGreater(score_with_food, score_no_food)

        # Score should be high because hunger is high
        print(f"Hunger: {stats.hunger}, Score with food: {score_with_food}")

        # Test Sleep
        stats.hunger = 0
        stats.energy = 10 # Tired
        score_sleep = self.ai.score_action("sleep", actions["sleep"], e, entities)
        print(f"Energy: {stats.energy}, Sleep Score: {score_sleep}")

        self.assertGreater(score_sleep, 0.5) # Should be high priority

if __name__ == "__main__":
    unittest.main()
