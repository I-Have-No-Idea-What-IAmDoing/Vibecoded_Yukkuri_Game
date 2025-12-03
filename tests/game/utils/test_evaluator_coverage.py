
import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.utils.evaluator import ConditionEvaluator
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, EmotionalState, Skills, Personality, SkillState

class TestConditionEvaluator:
    @pytest.fixture
    def evaluator(self):
        return ConditionEvaluator()

    @pytest.fixture
    def world(self):
        return MagicMock(spec=World)

    def test_evaluate_basic(self, evaluator):
        context = {"health": 100, "stress": 0}
        assert evaluator.evaluate("health > 50", context) is True
        assert evaluator.evaluate("health < 50", context) is False
        assert evaluator.evaluate("stress == 0", context) is True

    def test_evaluate_math_functions(self, evaluator):
        context = {"a": 10, "b": 20}
        assert evaluator.evaluate("min(a, b) == 10", context) is True
        assert evaluator.evaluate("max(a, b) == 20", context) is True

    def test_evaluate_has_trait(self, evaluator):
        context = {"traits": ["Kind", "Brave"]}
        assert evaluator.evaluate("has_trait('Kind')", context) is True
        assert evaluator.evaluate("has_trait('Lazy')", context) is False

        # Test with no traits in context
        assert evaluator.evaluate("has_trait('Kind')", {}) is False

    def test_evaluate_error_handling(self, evaluator):
        # Syntax Error
        assert evaluator.evaluate("health >", {"health": 100}) is False
        # Variable Missing
        assert evaluator.evaluate("unknown > 10", {}) is False

    def test_evaluate_type_coercion(self, evaluator):
        # Should return bool even if result is not bool, but log warning
        # result 10 -> True
        assert evaluator.evaluate("10", {}) is True
        # result 0 -> False
        assert evaluator.evaluate("0", {}) is False

    def test_build_context_full(self, evaluator, world):
        entity_id = 1

        # Mock Components
        stats = YukkuriStats(name="Test", type_id="reimu", health=80.0, hunger=20.0, discipline=50.0, age=100.0)

        pers = Personality()
        pers.traits.add("Kind")
        pers.axis.kindness = 10
        pers.axis.bravery = -10
        pers.axis.energy = 5
        pers.axis.greed = 0

        emo = EmotionalState(happiness=70.0, stress=10.0)

        skills = Skills()
        skills.states["scavenging"] = SkillState(level=2)

        def get_component(e, t):
            if t == YukkuriStats: return stats
            if t == Personality: return pers
            if t == EmotionalState: return emo
            if t == Skills: return skills
            return None

        world.get_component.side_effect = get_component

        context = evaluator.build_context(world, entity_id)

        assert context['health'] == 80.0
        assert context['hunger'] == 20.0
        assert context['stress'] == 10.0
        assert context['discipline'] == 50.0
        assert context['age'] == 100.0

        assert context['traits'] == ['Kind']
        assert context['kindness'] == 10
        assert context['bravery'] == -10

        assert context['happiness'] == 70.0
        # Mood check
        assert context['mood'] == "Content/Relaxed"

        assert context['skills']['scavenging'] == 2

    def test_build_context_missing_components(self, evaluator, world):
        entity_id = 2
        world.get_component.return_value = None

        context = evaluator.build_context(world, entity_id)

        # Context should be empty or minimal
        assert 'health' not in context
        assert 'happiness' not in context
        assert 'skills' in context # Skills defaults to empty map if missing but method initializes dict
        # Wait, implementation says:
        # skills = world.get_component(entity_id, Skills)
        # skill_map: Dict[str, int] = {}
        # if skills: ...
        # context['skills'] = skill_map
        # So 'skills' key exists and is empty dict.
        assert context['skills'] == {}

    def test_caching(self, evaluator):
        context = {"x": 10}
        # First pass parses
        assert evaluator.evaluate("x > 5", context) is True
        assert "x > 5" in evaluator._cache

        # Second pass uses cache (how to verify? Mock _eval? or assume it works if result is correct)
        # We can modify cache manually to verify it uses it
        evaluator._cache["x > 5"] = evaluator.evaluator.parse("x < 5").value # Flip logic hack

        # Should now return False if it uses cached AST
        assert evaluator.evaluate("x > 5", context) is False
