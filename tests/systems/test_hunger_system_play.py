
import unittest
import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, Needs, ItemStats, AIState, EmotionalState
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.game.systems.hunger_system import HungerSystem
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.skill_service import SkillService

class TestHungerSystemPlay(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.system = HungerSystem()
        
        # Mock services
        self.world.services.register(MagicMock(), AudioManager)
        self.world.services.register(MagicMock(), SkillService)

        # Setup Consumer
        self.consumer_id = self.world.create_entity(
            YukkuriStats(type_id="reimu", name="Tester"),
            Transform(x=100, y=100),
            Needs(hunger=50.0, bladder=0.0, energy=50.0),
            EmotionalState(happiness=0.0),
            AIState()
        )

        # Setup Toy (Item)
        # Fun=20, Nutrition=10 (should generally be 0 for toys, but testing isolation)
        self.item_id = self.world.create_entity(
            ItemStats(name="Ball", type_id="ball", cost=10, fun=20.0, nutrition=10.0, comfort=0.0),
            Transform(x=120, y=100) # Nearby
        )

    def test_play_does_not_consume_or_feed(self):
        """Test that playing (consume=False) increases happiness but ignores nutrition and destruction."""
        request = InteractionRequest(target_id=self.item_id, consume=False)
        consumer_trans = self.world.get_component(self.consumer_id, Transform)
        consumer_stats = self.world.get_component(self.consumer_id, YukkuriStats)
        item_stats = self.world.get_component(self.item_id, ItemStats)

        self.system.process_consumption(
            self.world, self.consumer_id, request, consumer_trans, consumer_stats, self.item_id, item_stats
        )

        # Assert Happiness Increased
        emotional = self.world.get_component(self.consumer_id, EmotionalState)
        self.assertEqual(emotional.happiness, 20.0, "Playing should increase happiness")

        # Assert Hunger Unchanged (Nutrition ignored)
        needs = self.world.get_component(self.consumer_id, Needs)
        self.assertEqual(needs.hunger, 50.0, "Playing should NOT decrease hunger")
        self.assertEqual(needs.bladder, 0.0, "Playing should NOT increase bladder")

        # Assert Item Still Exists
        self.assertTrue(self.world.entity_exists(self.item_id), "Item should NOT be destroyed")

    def test_eat_consumes_and_feeds(self):
        """Test that eating (consume=True) applies nutrition and destroys item."""
        request = InteractionRequest(target_id=self.item_id, consume=True)
        consumer_trans = self.world.get_component(self.consumer_id, Transform)
        consumer_stats = self.world.get_component(self.consumer_id, YukkuriStats)
        item_stats = self.world.get_component(self.item_id, ItemStats)

        self.system.process_consumption(
            self.world, self.consumer_id, request, consumer_trans, consumer_stats, self.item_id, item_stats
        )

        # Assert Happiness Increased (Eating tasty food is fun too)
        emotional = self.world.get_component(self.consumer_id, EmotionalState)
        self.assertEqual(emotional.happiness, 20.0, "Eating fun food should increase happiness")

        # Assert Hunger Decreased (Nutrition applied)
        needs = self.world.get_component(self.consumer_id, Needs)
        self.assertEqual(needs.hunger, 40.0, "Eating should decrease hunger (50 - 10)")
        self.assertEqual(needs.bladder, 5.0, "Eating should increase bladder (10 * 0.5)")

        # Assert Item Destroyed
        self.assertFalse(self.world.entity_exists(self.item_id), "Item SHOULD be destroyed")

if __name__ == "__main__":
    unittest.main()
