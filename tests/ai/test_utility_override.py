import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.ai.utility import UtilityAIEngine
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.yukkuri_components import Personality


class MockResourceManager:
    def __init__(self):
        self.ai_actions = {}


@pytest.fixture
def mock_rm():
    return MockResourceManager()


@pytest.fixture
def mock_trait_service():
    service = MagicMock(spec=TraitService)
    service.get_trait.return_value = None
    return service


def test_utility_override_by_trait(mock_rm, mock_trait_service):
    # Setup Action "Eat" with Consideration "Hunger"
    # Curve: Linear, m=1.0. Score = hunger/100 * 1.0.
    action_data = {
        "considerations": [
            {
                "name": "Hunger",
                "input": "hunger",
                "curve": "linear",
                "params": {"m": 1.0},
            }
        ],
        "weight": 1.0,
    }
    mock_rm.ai_actions = {"Eat": action_data}

    engine = UtilityAIEngine(mock_rm)

    # Setup Trait "GLUTTON" overriding "Hunger"
    # Curve: Linear, m=2.0. Score = hunger/100 * 2.0.
    glutton_data = {
        "ai_modifiers": {"Hunger": {"curve": "linear", "params": {"m": 2.0}}}
    }
    mock_trait_service.get_trait.side_effect = (
        lambda t: glutton_data if t == "GLUTTON" else None
    )

    # Context
    context = {"hunger": 50.0}

    # Case 1: No Personality
    score_normal = engine.actions["Eat"].calculate_utility(context)
    # 0.5 * 1.0 = 0.5
    assert score_normal == 0.5

    # Case 2: Personality with GLUTTON
    personality = Personality(traits={"GLUTTON"})

    # Manually calculate overrides (UtilitySelector does this usually)
    personality.cached_overrides = mock_trait_service.calculate_overrides(
        personality.traits
    )
    # Since mock_trait_service.calculate_overrides is not implemented in MagicMock unless we define it,
    # we should use the real method logic or mock it too.
    # The real TraitService.calculate_overrides just iterates and merges.
    # Let's mock calculate_overrides behavior or implement a simple mock side_effect.

    def calc_overrides(traits):
        overrides = {}
        for t in traits:
            td = mock_trait_service.get_trait(t)
            if td and "ai_modifiers" in td:
                overrides.update(td["ai_modifiers"])
        return overrides

    mock_trait_service.calculate_overrides.side_effect = calc_overrides

    personality.cached_overrides = mock_trait_service.calculate_overrides(
        personality.traits
    )

    # Select Action should use the overrides
    # But here we test calculate_utility directly with overrides passed from personality
    score_glutton = engine.actions["Eat"].calculate_utility(
        context, personality.cached_overrides
    )

    # 0.5 * 2.0 = 1.0
    assert score_glutton == 1.0


def test_select_action_integration(mock_rm, mock_trait_service):
    # Setup Action "Eat"
    mock_rm.ai_actions = {
        "Eat": {
            "considerations": [
                {
                    "name": "Hunger",
                    "input": "hunger",
                    "curve": "linear",
                    "params": {"m": 1.0},
                }
            ],
            "weight": 1.0,
        },
        "Play": {
            "considerations": [
                {
                    "name": "Boredom",
                    "input": "boredom",
                    "curve": "linear",
                    "params": {"m": 1.0},
                }
            ],
            "weight": 1.0,
        },
    }

    engine = UtilityAIEngine(mock_rm)

    # Context: Hunger 40, Boredom 40.
    # Normal: Eat=0.4, Play=0.4. Tie or order dependent.
    context = {"hunger": 40.0, "boredom": 40.0}

    # Setup Trait "GLUTTON" making Hunger more important (m=2.0)
    glutton_data = {
        "ai_modifiers": {"Hunger": {"curve": "linear", "params": {"m": 2.0}}}
    }
    mock_trait_service.get_trait.side_effect = (
        lambda t: glutton_data if t == "GLUTTON" else None
    )

    def calc_overrides(traits):
        overrides = {}
        for t in traits:
            td = mock_trait_service.get_trait(t)
            if td and "ai_modifiers" in td:
                overrides.update(td["ai_modifiers"])
        return overrides

    mock_trait_service.calculate_overrides.side_effect = calc_overrides

    # With GLUTTON
    personality = Personality(traits={"GLUTTON"})
    personality.cached_overrides = mock_trait_service.calculate_overrides(
        personality.traits
    )

    action = engine.select_action(context, personality, mock_trait_service)

    # Eat score: 0.4 * 2.0 = 0.8
    # Play score: 0.4 * 1.0 = 0.4
    # Should choose Eat
    assert action == "Eat"
