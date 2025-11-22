import unittest
from unittest.mock import MagicMock
from src.yukkuri_game.game.services import GameService
from src.yukkuri_game.game.yukkuri_components import YukkuriStats
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.audio import AudioManager

class TestSocialInteractions(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.game_service = GameService(self.world)
        self.audio_manager = MagicMock()
        # The service locator uses register(instance, service_type) signature or defaults to type(instance)
        # In TestSocialInteractions.setUp, call register(self.audio_manager, AudioManager)
        self.world.services.register(self.audio_manager, AudioManager)

        # Create two yukkuris
        self.yukkuri1 = self.world.create_entity()
        self.yukkuri2 = self.world.create_entity()

        self.stats1 = YukkuriStats(name="Y1", type_id="reimu")
        self.stats2 = YukkuriStats(name="Y2", type_id="reimu")
        self.stats3 = YukkuriStats(name="Y3", type_id="marisa")

        self.world.add_component(self.yukkuri1, self.stats1)
        self.world.add_component(self.yukkuri2, self.stats2)

    def test_talk_interaction(self):
        # Initial state
        self.stats1.happiness = 50.0
        self.stats1.social = 50.0
        self.stats2.happiness = 50.0
        self.stats2.social = 50.0

        success = self.game_service.interact_social(self.yukkuri1, self.yukkuri2, "Talk")
        self.assertTrue(success)

        # Verify stats changes
        self.assertAlmostEqual(self.stats1.happiness, 55.0)
        self.assertAlmostEqual(self.stats1.social, 65.0)
        self.assertAlmostEqual(self.stats2.happiness, 55.0)
        self.assertAlmostEqual(self.stats2.social, 65.0)

        # Verify audio
        self.audio_manager.play_sound.assert_called_with("talk")

    def test_fight_interaction(self):
        # Setup incompatible yukkuri for fight logic (though interact_social doesn't check type compatibility,
        # the caller usually does, but we test the effect here)
        self.world.add_component(self.yukkuri2, self.stats3) # Change stats2 to be marisa

        self.stats1.health = 100.0
        self.stats3.health = 100.0
        self.stats1.stress = 0.0
        self.stats3.stress = 0.0

        success = self.game_service.interact_social(self.yukkuri1, self.yukkuri2, "Fight")
        self.assertTrue(success)

        # Verify stats changes
        self.assertLess(self.stats1.health, 100.0)
        self.assertLess(self.stats3.health, 100.0)
        self.assertGreater(self.stats1.stress, 0.0)
        self.assertGreater(self.stats3.stress, 0.0)

        # Verify audio
        self.audio_manager.play_sound.assert_called_with("hit")

    def test_dance_interaction(self):
        success = self.game_service.interact_social(self.yukkuri1, self.yukkuri2, "Dance")
        self.assertTrue(success)

        self.assertGreater(self.stats1.happiness, 50.0)
        self.assertGreater(self.stats2.happiness, 50.0)

if __name__ == '__main__':
    unittest.main()
