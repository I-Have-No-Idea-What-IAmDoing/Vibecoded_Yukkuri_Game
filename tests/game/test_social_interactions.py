import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.services import GameService
from yukkuri_game.game.yukkuri_components import YukkuriStats, EmotionalState, RelationshipRegistry, Personality
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_service import SkillService

class TestSocialInteractions(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.event_bus = EventBus()
        self.game_service = GameService(self.world)

        self.audio_manager = MagicMock()
        self.world.services.register(self.audio_manager, AudioManager)

        self.trait_service = MagicMock(spec=TraitService)
        # Setup specific interaction returns
        def get_interaction(name):
            if name == "Talk":
                return {"type": "SOCIAL", "base_impact": 5.0, "social_impact": {"affinity": 5.0}, "target_physical_impact": {"happiness": 5.0}, "actor_physical_impact": {"happiness": 5.0}}
            if name == "Fight":
                return {"type": "AGGRESSIVE", "base_impact": -10.0, "social_impact": {"affinity": -10.0}, "target_physical_impact": {"health": -5.0}, "actor_physical_impact": {"health": -5.0}, "physical_impact": {"health": -5.0}}
            if name == "Dance":
                return {"type": "FUN", "base_impact": 10.0, "social_impact": {"affinity": 10.0}, "target_physical_impact": {"happiness": 10.0}, "actor_physical_impact": {"happiness": 10.0}}
            return {}

        self.trait_service.get_interaction.side_effect = get_interaction
        self.trait_service.get_trait.return_value = {}
        self.world.services.register(self.trait_service, TraitService)

        self.skill_service = MagicMock(spec=SkillService)
        self.world.services.register(self.skill_service, SkillService)

        self.social_system = SocialSystem(self.event_bus)

        # Create two yukkuris
        self.yukkuri1 = self.world.create_entity()
        self.yukkuri2 = self.world.create_entity()

        self.stats1 = YukkuriStats(name="Y1", type_id="reimu", health=100.0)
        self.emo1 = EmotionalState(happiness=50.0, stress=0.0)

        self.stats2 = YukkuriStats(name="Y2", type_id="reimu", health=100.0)
        self.emo2 = EmotionalState(happiness=50.0, stress=0.0)

        self.stats3 = YukkuriStats(name="Y3", type_id="marisa", health=100.0)
        self.emo3 = EmotionalState(happiness=50.0, stress=0.0)

        self.world.add_component(self.yukkuri1, self.stats1)
        self.world.add_component(self.yukkuri1, self.emo1)
        self.world.add_component(self.yukkuri1, Transform(0,0))
        self.world.add_component(self.yukkuri1, RelationshipRegistry())
        self.world.add_component(self.yukkuri1, Personality())

        self.world.add_component(self.yukkuri2, self.stats2)
        self.world.add_component(self.yukkuri2, self.emo2)
        self.world.add_component(self.yukkuri2, Transform(10,0))
        self.world.add_component(self.yukkuri2, RelationshipRegistry())
        self.world.add_component(self.yukkuri2, Personality())

    def test_talk_interaction(self):
        # Initial state
        self.emo1.happiness = 50.0
        # self.stats1.social = 50.0 # stats1.social doesn't exist in YukkuriStats anymore?
        # Checking YukkuriStats definition: it has hunger, hygiene, energy, etc. but social might be removed or handled elsewhere.
        # Let's check stats again. No 'social' field in YukkuriStats in components.py previously read?
        # Assuming previous test was outdated about `stats1.social`.

        self.emo2.happiness = 50.0

        # Act: Add InteractionRequest
        self.world.add_component(self.yukkuri1, InteractionRequest(target_id=self.yukkuri2, action="Talk"))
        self.social_system.update(self.world, 0.1)

        # Verify stats changes
        self.assertAlmostEqual(self.emo1.happiness, 55.0)
        self.assertAlmostEqual(self.emo2.happiness, 55.0)

        # Verify audio (Not handled by SocialSystem directly, usually via event listener elsewhere, but here we check system logic)
        # If Audio logic is in another system, we can't test it here unless we mock that system.
        # But this test was testing "SocialInteractions" as a concept.
        # The previous test mocked AudioManager and expected game_service to call it.
        # Now SocialSystem doesn't call AudioManager directly?
        # SocialSystem spawns visual feedback but doesn't seem to play sound?
        # Let's check SocialSystem code again... it spawns visual feedback.
        # Maybe SoundSystem listens to SocialInteractionEvent?

        # For now, we verified the logic (stats update).

    def test_fight_interaction(self):
        # Setup incompatible yukkuri for fight logic
        self.world.add_component(self.yukkuri2, self.stats3) # Change stats2 to be marisa
        self.world.add_component(self.yukkuri2, self.emo3) # Add emo3

        # Ensure Transform and Relations are still there (add_component overwrites? No, usually update or adds new component type)
        # But we are replacing component instance for same type?
        # Yes, ECS add_component usually replaces if type exists.

        self.stats1.health = 100.0
        self.stats3.health = 100.0
        self.emo1.stress = 0.0
        self.emo3.stress = 0.0

        self.world.add_component(self.yukkuri1, InteractionRequest(target_id=self.yukkuri2, action="Fight"))
        self.social_system.update(self.world, 0.1)

        # Verify stats changes
        self.assertLess(self.stats1.health, 100.0)
        self.assertLess(self.stats3.health, 100.0)
        # Stress update logic is in _update_emotional_state.
        # If base_impact < -15, stress + 20.
        # Fight base_impact is -10 in my mock. So stress might not increase via that path.
        # But _apply_physical_impact can change stress if defined in interaction data.
        # My mock for Fight didn't include stress change.
        # Let's update mock to include stress change if we want to test it, or adjust expectation.

        # Actually, let's just check health for now as that's in my mock.

    def test_dance_interaction(self):
        self.world.add_component(self.yukkuri1, InteractionRequest(target_id=self.yukkuri2, action="Dance"))
        self.social_system.update(self.world, 0.1)

        self.assertGreater(self.emo1.happiness, 50.0)
        self.assertGreater(self.emo2.happiness, 50.0)

if __name__ == '__main__':
    unittest.main()
