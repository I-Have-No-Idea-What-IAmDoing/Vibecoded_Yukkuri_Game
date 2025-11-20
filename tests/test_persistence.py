import unittest
import os
import json
from src.systems.data_loader import DataLoader
from src.core.yukkurrium import Yukkurrium
from src.systems.persistence import Persistence
from src.core.game import Game

class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(data_dir='data')
        self.loader.load_all()
        self.game = Game(self.loader)
        self.persistence = Persistence(filepath='test_save.json')

    def tearDown(self):
        if os.path.exists('test_save.json'):
            os.remove('test_save.json')

    def test_save_load_items(self):
        # Place items with keys that differ from names (e.g. Bed -> Soft Bed)
        self.game.yukkurrium.money = 1000
        self.game.yukkurrium.place_item("Bed", 100, 100)
        self.game.yukkurrium.place_item("BeanPaste", 200, 200)

        self.assertEqual(len(self.game.yukkurrium.items), 2)

        # Save
        self.persistence.save_game(self.game)

        # Clear
        self.game.yukkurrium.items = []
        self.game.yukkurrium.money = 0

        # Load
        self.persistence.load_game(self.game)

        self.assertEqual(len(self.game.yukkurrium.items), 2)
        self.assertEqual(self.game.yukkurrium.items[0].type_key, "Bed")
        self.assertEqual(self.game.yukkurrium.items[0].name, "Soft Bed")
        self.assertAlmostEqual(self.game.yukkurrium.money, 900 - 10) # 1000 - 100 - 10 = 890. Wait.
        # Initial: 1000.
        # Place Bed: -100 => 900.
        # Place BeanPaste: -10 => 890.
        # Save money: 890.
        # Clear money: 0.
        # Load money: 890.

        self.assertEqual(self.game.yukkurrium.money, 890)

if __name__ == '__main__':
    unittest.main()
