import unittest
from unittest.mock import MagicMock
from yukkuri_game.game.services import GameService
from yukkuri_game.game.yukkuri_components import (
    YukkuriStats,
    Needs,
    EmotionalState,
    RelationshipRegistry,
    Personality,
)
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_service import SkillService


class TestSocialInteractions(unittest.TestCase):
    def setUp(self):
        from test_utils import make_configured_world
        from yukkuri_game.engine.event_bus import EventBus
        self.world = make_configured_world()
        self.event_bus = self.world.services.get(EventBus)
        self.game_service = GameService(self.world)

        self.audio_manager = MagicMock()
        self.world.services.register(self.audio_manager, AudioManager)

        self.trait_service = MagicMock(spec=TraitService)

        # Setup specific interaction returns
        def get_interaction(name):
            if name == "Talk":
                return {
                    "type": "SOCIAL",
                    "base_impact": 5.0,
                    "social_impact": {"affinity": 5.0},
                    "target_physical_impact": {"happiness": 5.0},
                    "actor_physical_impact": {"happiness": 5.0},
                }
            if name == "Fight":
                return {
                    "type": "AGGRESSIVE",
                    "base_impact": -10.0,
                    "social_impact": {"affinity": -10.0},
                    "target_physical_impact": {"health": -5.0},
                    "actor_physical_impact": {"health": -5.0},
                    "physical_impact": {"health": -5.0},
                }
            if name == "Dance":
                return {
                    "type": "FUN",
                    "base_impact": 10.0,
                    "social_impact": {"affinity": 10.0},
                    "target_physical_impact": {"happiness": 10.0},
                    "actor_physical_impact": {"happiness": 10.0},
                }
            return {}

        self.trait_service.get_interaction.side_effect = get_interaction
        self.trait_service.get_trait.return_value = {}
        # Also need calculate_overrides for InteractionSystem
        self.trait_service.calculate_overrides.return_value = {}
        self.world.services.register(self.trait_service, TraitService)

        self.skill_service = MagicMock(spec=SkillService)
        self.world.services.register(self.skill_service, SkillService)

        self.social_system = SocialSystem()
        self.world.services.register(self.social_system, SocialSystem)
        self.world.add_system(self.social_system)

        self.interaction_system = InteractionSystem()
        self.world.add_system(self.interaction_system)

        # Create two yukkuris
        self.yukkuri1 = self.world.create_entity()
        self.yukkuri2 = self.world.create_entity()

        self.stats1 = YukkuriStats(name="Y1", type_id="reimu")
        self.needs1 = Needs(health=100.0)
        self.emo1 = EmotionalState(happiness=50.0, stress=0.0)

        self.stats2 = YukkuriStats(name="Y2", type_id="reimu")
        self.needs2 = Needs(health=100.0)
        self.emo2 = EmotionalState(happiness=50.0, stress=0.0)

        self.stats3 = YukkuriStats(name="Y3", type_id="marisa")
        self.needs3 = Needs(health=100.0)
        self.emo3 = EmotionalState(happiness=50.0, stress=0.0)

        self.world.add_component(self.yukkuri1, self.stats1)
        self.world.add_component(self.yukkuri1, self.needs1)
        self.world.add_component(self.yukkuri1, self.emo1)
        self.world.add_component(self.yukkuri1, Transform(0, 0))
        self.world.add_component(self.yukkuri1, RelationshipRegistry())
        self.world.add_component(self.yukkuri1, Personality())

        self.world.add_component(self.yukkuri2, self.stats2)
        self.world.add_component(self.yukkuri2, self.needs2)
        self.world.add_component(self.yukkuri2, self.emo2)
        self.world.add_component(self.yukkuri2, Transform(10, 0))
        self.world.add_component(self.yukkuri2, RelationshipRegistry())
        self.world.add_component(self.yukkuri2, Personality())

    def test_talk_interaction(self) -> None:
        # Initial state
        self.emo1.happiness = 50.0
        self.emo2.happiness = 50.0

        # Act: Add InteractionRequest
        self.world.add_component(
            self.yukkuri1, InteractionRequest(target_id=self.yukkuri2, action="Talk")
        )

        # Use interaction system to process request
        self.interaction_system.update(self.world, 0.1)

        # Verify stats changes
        self.assertAlmostEqual(self.emo1.happiness, 55.0)
        self.assertAlmostEqual(self.emo2.happiness, 55.0)

    def test_fight_interaction(self) -> None:
        # Setup incompatible yukkuri for fight logic
        self.world.add_component(
            self.yukkuri2, self.stats3
        )  # Change stats2 to be marisa
        self.world.add_component(self.yukkuri2, self.needs3)
        self.world.add_component(self.yukkuri2, self.emo3)  # Add emo3

        self.needs1.health = 100.0
        self.needs3.health = 100.0
        self.emo1.stress = 0.0
        self.emo3.stress = 0.0

        self.world.add_component(
            self.yukkuri1, InteractionRequest(target_id=self.yukkuri2, action="Fight")
        )
        self.interaction_system.update(self.world, 0.1)

        # Verify stats changes
        self.assertLess(self.needs1.health, 100.0)
        self.assertLess(self.needs3.health, 100.0)

    def test_dance_interaction(self) -> None:
        self.world.add_component(
            self.yukkuri1, InteractionRequest(target_id=self.yukkuri2, action="Dance")
        )
        self.interaction_system.update(self.world, 0.1)

        self.assertGreater(self.emo1.happiness, 50.0)
        self.assertGreater(self.emo2.happiness, 50.0)


if __name__ == "__main__":
    unittest.main()
