import unittest
from src.utils.loader import game_data
from src.engine.ecs import Entity
from src.engine.components import Stats, AIComponent
from src.engine.utility_ai import UtilityAI

class TestPeerInteraction(unittest.TestCase):
    def setUp(self):
        game_data.load_all()
        self.ai = UtilityAI()

    def test_talk_score(self):
        """Test that Talk action is viable when partner is present."""
        me = Entity()
        me.add_component(Stats(happiness=50, max_happiness=100)) # Kind of sad

        entities = [me]

        # No partner
        score_alone = self.ai.score_action("talk", game_data.ai_actions["talk"], me, entities)

        # Add partner
        partner = Entity()
        partner.add_component(Stats()) # Just needs to exist with stats for our simple check
        entities.append(partner)

        score_with_partner = self.ai.score_action("talk", game_data.ai_actions["talk"], me, entities)

        self.assertGreater(score_with_partner, score_alone)
        self.assertGreater(score_with_partner, 0.0)

if __name__ == "__main__":
    unittest.main()
