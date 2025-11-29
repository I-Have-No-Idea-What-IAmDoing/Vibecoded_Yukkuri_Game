import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats, EmotionalState
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.engine.ecs import World

class TestInteractionSystemFix(unittest.TestCase):
    def test_interaction_happiness_update_bug(self):
        """
        Test that interaction with a fun item updates EmotionalState.happiness,
        not YukkuriStats.happiness (which doesn't exist).
        """
        world = World()
        system = InteractionSystem()
        world.add_system(system)

        # Create consumer
        consumer = world.create_entity()
        stats = YukkuriStats(name="Yukkuri", type_id="test")
        emotional = EmotionalState(happiness=50.0)
        transform = Transform(x=0, y=0)

        world.add_component(consumer, stats)
        world.add_component(consumer, emotional)
        world.add_component(consumer, transform)

        # Create item
        item = world.create_entity()
        item_stats = ItemStats(name="Toy", type_id="toy", cost=10, fun=20.0)
        item_transform = Transform(x=0, y=0) # Same location

        world.add_component(item, item_stats)
        world.add_component(item, item_transform)

        # Create interaction request
        request = InteractionRequest(target_id=item, consume=False)
        world.add_component(consumer, request)

        # Run system
        system.update(world, 0.1)

        # Check results
        # 1. Request should be removed
        self.assertFalse(world.has_component(consumer, InteractionRequest))

        # 2. EmotionalState happiness should increase
        # 50 + 20 = 70
        self.assertEqual(emotional.happiness, 70.0)
