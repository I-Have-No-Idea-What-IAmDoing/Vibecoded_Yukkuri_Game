import unittest
from src.systems.data_loader import DataLoader
from src.ai.utility_ai import UtilityAIEngine
from src.entities.yukkuri import Yukkuri
from src.core.yukkurrium import Yukkurrium

class TestUtilityAI(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(data_dir='data')
        self.loader.load_all()
        self.engine = UtilityAIEngine(self.loader)
        self.yukkurrium = Yukkurrium(800, 600, self.loader)

        # Mock Yukkuri
        reimu_data = self.loader.get_yukkuri_type("Reimu")
        self.yukkuri = Yukkuri(reimu_data, 0, 0)

    def test_hunger_logic(self):
        # Simulate high hunger (low stats['hunger'])
        self.yukkuri.stats['hunger'] = 0

        eat_action_data = self.loader.get_action("Eat")
        score = self.engine.calculate_utility(self.yukkuri, eat_action_data)

        # With hunger 0 (starving), utility should be high
        # My logic was: val = 100 - hunger(0) = 100.
        # Curve: logit, slope 1.0. Input 100 -> High Score.
        self.assertGreater(score, 50)

    def test_full_logic(self):
        # Simulate full (high stats['hunger'])
        self.yukkuri.stats['hunger'] = 100

        eat_action_data = self.loader.get_action("Eat")
        score = self.engine.calculate_utility(self.yukkuri, eat_action_data)

        # With hunger 100, val = 0. Input 0 -> Low Score.
        # Base score is 0.
        self.assertLess(score, 50)

if __name__ == '__main__':
    unittest.main()
