import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.services import GameService
from yukkuri_game.game.yukkuri_components import YukkuriStats, EmotionalState
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.trait_service import TraitService

class TestSocialInteractions(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.game_service = GameService(self.world)
        self.audio_manager = MagicMock()
        # Mock the AudioManager instance itself if register expects an instance
        # The previous register call was correct if MagicMock() mimics the instance.
        # However, ServiceLocator stores by type.
        # If I call try_get(AudioManager), it uses AudioManager as key.
        # So I need to register using AudioManager key.
        self.world.services.register(self.audio_manager, AudioManager)

        # Mock TraitService
        self.trait_service = MagicMock(spec=TraitService)
        self.world.services.register(self.trait_service, TraitService)

        # Setup Interaction Data Mocks
        def get_interaction_mock(name):
            data = MagicMock()
            if name == "Talk":
                data.base_impact = 10.0
                data.physical_impact = {"happiness": 5.0} # Add happiness effect explicitly to match test expectation
                data.social_impact = {"affinity": 5.0, "familiarity": 5.0}
            elif name == "Fight":
                data.base_impact = -20.0
                data.physical_impact = {"health": -10.0, "stress": 10.0}
                data.social_impact = {"affinity": -10.0, "fear": 10.0}
            elif name == "Dance":
                data.base_impact = 20.0 # Enough to trigger happiness > 50 check
                data.social_impact = {"affinity": 10.0}
            else:
                return None

            # Mock dict access for _get_attr helper in SocialSystem
            def get_item(key, default=None):
                if key == "base_impact": return data.base_impact
                if key == "social_impact": return data.social_impact
                if key == "physical_impact": return getattr(data, "physical_impact", {})
                if key == "conditions": return []
                if key == "modifiers": return {}
                if key == "type": return name
                return default

            data.get = get_item
            return data

        self.trait_service.get_interaction.side_effect = get_interaction_mock

        # Create two yukkuris
        self.yukkuri1 = self.world.create_entity()
        self.yukkuri2 = self.world.create_entity()

        self.stats1 = YukkuriStats(name="Y1", type_id="reimu")
        self.emo1 = EmotionalState(happiness=50.0, stress=0.0)

        self.stats2 = YukkuriStats(name="Y2", type_id="reimu")
        self.emo2 = EmotionalState(happiness=50.0, stress=0.0)

        self.stats3 = YukkuriStats(name="Y3", type_id="marisa")
        self.emo3 = EmotionalState(happiness=50.0, stress=0.0)

        self.world.add_component(self.yukkuri1, self.stats1)
        self.world.add_component(self.yukkuri1, self.emo1)
        self.world.add_component(self.yukkuri2, self.stats2)
        self.world.add_component(self.yukkuri2, self.emo2)

    def test_talk_interaction(self):
        # Initial state
        self.emo1.happiness = 50.0
        self.stats1.social = 50.0
        self.emo2.happiness = 50.0
        self.stats2.social = 50.0

        success = self.game_service.interact_social(self.yukkuri1, self.yukkuri2, "Talk")
        self.assertTrue(success)

        # Verify stats changes
        self.assertAlmostEqual(self.emo1.happiness, 55.0)
        # self.assertAlmostEqual(self.stats1.social, 65.0) # Social stat not updated by new system
        self.assertAlmostEqual(self.emo2.happiness, 55.0)
        # self.assertAlmostEqual(self.stats2.social, 65.0) # Social stat not updated by new system

        # Verify audio
        self.audio_manager.play_sound.assert_called_with("talk")

    def test_fight_interaction(self):
        # Setup incompatible yukkuri for fight logic (though interact_social doesn't check type compatibility,
        # the caller usually does, but we test the effect here)
        self.world.add_component(self.yukkuri2, self.stats3) # Change stats2 to be marisa
        self.world.add_component(self.yukkuri2, self.emo3) # Add emo3

        self.stats1.health = 100.0
        self.stats3.health = 100.0
        self.emo1.stress = 0.0
        self.emo3.stress = 0.0

        success = self.game_service.interact_social(self.yukkuri1, self.yukkuri2, "Fight")
        self.assertTrue(success)

        # Verify stats changes
        self.assertLess(self.stats1.health, 100.0)
        self.assertLess(self.stats3.health, 100.0)
        self.assertGreater(self.emo1.stress, 0.0)
        self.assertGreater(self.emo3.stress, 0.0)

        # Verify audio
        self.audio_manager.play_sound.assert_called_with("hit")

    def test_dance_interaction(self):
        success = self.game_service.interact_social(self.yukkuri1, self.yukkuri2, "Dance")
        self.assertTrue(success)

        self.assertGreater(self.emo1.happiness, 50.0)
        self.assertGreater(self.emo2.happiness, 50.0)

if __name__ == '__main__':
    unittest.main()
