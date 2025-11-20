import unittest
import os
import yaml
from src.systems.data_loader import DataLoader

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(data_dir='data')

    def test_load_yukkuri_types(self):
        self.loader.load_all()
        self.assertIn("Reimu", self.loader.yukkuri_types)
        self.assertEqual(self.loader.yukkuri_types["Reimu"]["base_health"], 100)

    def test_load_items(self):
        self.loader.load_all()
        self.assertIn("BeanPaste", self.loader.items)
        self.assertEqual(self.loader.items["BeanPaste"]["cost"], 10)

    def test_load_ai_actions(self):
        self.loader.load_all()
        self.assertIn("Eat", self.loader.ai_actions)
        self.assertEqual(self.loader.ai_actions["Eat"]["type"], "interaction")

if __name__ == '__main__':
    unittest.main()
