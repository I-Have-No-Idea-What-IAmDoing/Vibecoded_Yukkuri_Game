"""
Tests for the Utility AI system.
"""

import pytest

from game.core.ai.ai_system import AIController
from game.core.data.loader import GameData
from game.core.ecs.components import Needs, AIProfile
from game.core.state.game_state import GameState


@pytest.fixture
def game_data() -> GameData:
    """Provides mock game data for testing."""
    gd = GameData()
    gd.yukkuris = {
        "test_yukkuri": {
            "id": "test_yukkuri", "display_name_key": "yukkuri.test",
            "base_needs": {"hunger": 0.1, "energy": 0.9},
            "personality": {}, "ai_profile": "test_profile"
        }
    }
    gd.behaviors = {
        "test_profile": {
            "actions": [
                {
                    "id": "eat", "cooldown": 1.0,
                    "considerations": [
                        {"type": "need_level", "need": "hunger", "curve": "linear", "weight": 1.0}
                    ]
                },
                {
                    "id": "sleep", "cooldown": 1.0,
                    "considerations": [
                        {"type": "need_inverse", "need": "energy", "curve": "linear", "weight": 1.0}
                    ]
                }
            ]
        }
    }
    return gd


def test_ai_chooses_eat_when_hungry(game_data: GameData):
    """
    Tests that the AI chooses the 'eat' action when hunger is high.
    """
    game_state = GameState(game_data)
    yukkuri = game_state.create_yukkuri("test_yukkuri", 0, 0)

    needs = yukkuri.get_component(Needs)
    needs.values["hunger"] = 0.9  # Very hungry
    needs.values["energy"] = 0.8  # Not tired

    profile = yukkuri.get_component(AIProfile)
    ai_controller = AIController(profile.behavior["actions"], game_state)
    best_action = ai_controller.decide(yukkuri)

    assert best_action is not None
    assert best_action.schema["id"] == "eat"


def test_ai_chooses_sleep_when_tired(game_data: GameData):
    """
    Tests that the AI chooses the 'sleep' action when energy is low.
    """
    game_state = GameState(game_data)
    yukkuri = game_state.create_yukkuri("test_yukkuri", 0, 0)

    needs = yukkuri.get_component(Needs)
    needs.values["hunger"] = 0.1  # Not hungry
    needs.values["energy"] = 0.2  # Very tired

    profile = yukkuri.get_component(AIProfile)
    ai_controller = AIController(profile.behavior["actions"], game_state)
    best_action = ai_controller.decide(yukkuri)

    assert best_action is not None
    assert best_action.schema["id"] == "sleep"
