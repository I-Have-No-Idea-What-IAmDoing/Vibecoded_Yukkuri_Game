import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.ai.utility import UtilityAIEngine, Action, Consideration
from yukkuri_game.engine.data_models import AIData, AIAction, ActionEffect, ActionConsideration
from yukkuri_game.game.services import TraitService
from yukkuri_game.game.yukkuri_components import Personality

class MockResourceManager:
    def __init__(self, actions_data):
        self.ai_actions = actions_data

@pytest.fixture
def trait_service(tmp_path):
    traits_dir = tmp_path / "data" / "traits"
    traits_dir.mkdir(parents=True)
    traits_file = traits_dir / "traits.toml"
    traits_file.write_text("""
    [traits.GESU]
    name = "Gesu"
    [traits.GESU.ai_modifiers]
    "Empathy" = { curve = "linear", params = { m = 0.0 } }
    """)

    interactions_dir = tmp_path / "data" / "ai"
    interactions_dir.mkdir(parents=True)
    interactions_file = interactions_dir / "interactions.toml"
    interactions_file.write_text("")

    return TraitService(str(tmp_path / "data"))

def test_curve_override(trait_service):
    mock_actions = {
        "Social": AIAction(
            weight=1.0,
            effects=ActionEffect(type="test", stat_changes={}),
            considerations=[
                ActionConsideration(name="Empathy", input="social", curve="linear", params={"m": 1.0, "b": 0.0})
            ]
        )
    }
    rm = MockResourceManager(mock_actions)
    engine = UtilityAIEngine(rm)
    engine.set_trait_service(trait_service)

    # Default behavior: score = social / 100
    context_normal = {"social": 100.0, "__personality__": Personality()}
    assert engine.actions["Social"].calculate_utility(context_normal, trait_service) == 1.0

    # Override behavior (Gesu trait): slope 0.0 -> score 0.0
    pers_gesu = Personality(traits={"GESU"})
    context_gesu = {"social": 100.0, "__personality__": pers_gesu}
    assert engine.actions["Social"].calculate_utility(context_gesu, trait_service) == 0.0
