import unittest
from src.systems.data_loader import DataLoader
from src.ai.utility_ai import UtilityAIEngine
from src.entities.yukkuri import Yukkuri
from src.core.yukkurrium import Yukkurrium

class TestAILogic(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(data_dir='data')
        self.loader.load_all()
        self.engine = UtilityAIEngine(self.loader)
        self.yukkurrium = Yukkurrium(800, 600, self.loader)

        reimu_data = self.loader.get_yukkuri_type("Reimu")
        self.yukkuri = Yukkuri(reimu_data, 0, 0)

    def test_wander_termination(self):
        # Force wander action
        self.yukkuri.current_action = "Wander"

        # Update for a small amount of time
        self.engine.execute_action("Wander", self.yukkuri, self.yukkurrium, 1.0)
        self.assertEqual(self.yukkuri.current_action, "Wander") # Should still be wandering

        # Update for enough time to exceed 2.0s threshold
        self.engine.execute_action("Wander", self.yukkuri, self.yukkurrium, 1.5)
        # Total time 2.5s > 2.0s

        self.assertIsNone(self.yukkuri.current_action) # Should have finished

    def test_energy_decay(self):
        initial_energy = self.yukkuri.stats['energy']
        self.yukkuri.update(1.0)
        self.assertLess(self.yukkuri.stats['energy'], initial_energy)

if __name__ == '__main__':
    unittest.main()
