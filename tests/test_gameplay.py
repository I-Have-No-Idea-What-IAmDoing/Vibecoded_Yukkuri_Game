import unittest
from src.utils.loader import game_data
from src.engine.game import Game
from src.engine.components import Stats, ItemComponent

class TestGameplay(unittest.TestCase):
    def setUp(self):
        game_data.load_all()
        self.game = Game()
        self.game.initialize() # Initialize systems and spawn initial entities

    def test_spawn_item(self):
        """Test buying and spawning items."""
        initial_money = self.game.state.money
        item_id = "food_pellet"
        cost = game_data.items[item_id]["cost"]

        self.game.spawn_item(item_id, 100, 100)

        # Check money deducted
        self.assertEqual(self.game.state.money, initial_money - cost)

        # Check item entity exists
        items = [e for e in self.game.ecs.entities if e.get_component(ItemComponent)]
        self.assertTrue(any(e.get_component(ItemComponent).item_type == "food" for e in items))

    def test_cleanliness_stat(self):
        """Test cleanliness stat exists and decays."""
        # Find a yukkuri
        yukkuri = next(e for e in self.game.ecs.entities if e.get_component(Stats))
        stats = yukkuri.get_component(Stats)

        self.assertEqual(stats.cleanliness, 100.0)

        # Run simulation for a bit
        dt = 1.0
        self.game.ecs.update(dt, self.game.state)

        # Cleanliness should decay
        self.assertLess(stats.cleanliness, 100.0)

if __name__ == "__main__":
    unittest.main()
