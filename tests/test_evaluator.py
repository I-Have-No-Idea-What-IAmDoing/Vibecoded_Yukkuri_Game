import pytest
from unittest.mock import MagicMock, patch
from loguru import logger
from src.yukkuri_game.game.utils.evaluator import ConditionEvaluator
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, Needs, EmotionalState, Skills, Personality, SkillState

def test_evaluator_basic():
    evaluator = ConditionEvaluator()
    ctx = {"val": 10, "nested": {"a": 5}}

    assert evaluator.evaluate("val > 5", ctx)
    assert not evaluator.evaluate("val < 5", ctx)
    assert evaluator.evaluate("nested.a == 5", ctx)

def test_evaluator_build_context():
    evaluator = ConditionEvaluator()
    world = MagicMock(spec=World)
    entity_id = 1

    # Mock components
    stats = YukkuriStats(name="Test", type_id="test", discipline=50.0)
    needs = Needs(health=80.0, hunger=20.0)
    emotion = EmotionalState(happiness=10.0, stress=5.0)
    skills = Skills(states={"combat": SkillState(level=10), "social": SkillState(level=2)})
    pers = Personality(traits={"GESU"}, axis=None)

    # Setup world.get_component side effects
    def get_component(eid, comp_type):
        if comp_type == YukkuriStats: return stats
        if comp_type == Needs: return needs
        if comp_type == EmotionalState: return emotion
        if comp_type == Skills: return skills
        if comp_type == Personality: return pers
        return None

    world.get_component.side_effect = get_component

    ctx = evaluator.build_context(world, entity_id)

    assert ctx['health'] == 80.0
    assert ctx['skills']['combat'] == 10
    assert ctx['skills']['social'] == 2
    assert "GESU" in ctx['traits']

    # Test expressions against context
    assert evaluator.evaluate("health > 50", ctx)
    assert evaluator.evaluate("skills.combat > 5", ctx)
    assert evaluator.evaluate("has_trait('GESU')", ctx)
    assert evaluator.evaluate("'GESU' in traits", ctx)
    assert not evaluator.evaluate("skills.social > 5", ctx)

def test_evaluator_missing_components():
    evaluator = ConditionEvaluator()
    world = MagicMock(spec=World)
    world.get_component.return_value = None

    ctx = evaluator.build_context(world, 1)

    # Check defaults or absence
    # health might be missing if stats/needs missing
    assert 'health' not in ctx
    assert ctx['skills'] == {}

    # Exception handling
    # "health" is undefined -> NameError caught, returns False
    assert evaluator.evaluate("health > 50", ctx) is False

def test_evaluator_type_checking():
    messages = []
    handler_id = logger.add(lambda msg: messages.append(msg))
    try:
        evaluator = ConditionEvaluator()
        ctx = {"val": 10}

        # Returns int (15), expecting bool -> Warning
        result = evaluator.evaluate("val + 5", ctx)
        assert result is True # 15 is True

        # Check messages
        log_msg = "Expression 'val + 5' evaluated to int (15) instead of bool."
        assert any(log_msg in str(m) for m in messages)

        # Returns bool -> No warning
        messages.clear()
        evaluator.evaluate("val > 5", ctx)
        assert not any(log_msg in str(m) for m in messages)

    finally:
        logger.remove(handler_id)

def test_mood_injection():
    evaluator = ConditionEvaluator()
    world = MagicMock(spec=World)
    entity_id = 1

    emotion = EmotionalState(happiness=50.0, stress=0.0)
    pers = Personality(traits=set(), axis=None) # Default axis is 0 bravery

    def side_effect(eid, t):
        if t == EmotionalState: return emotion
        if t == Personality: return pers
        return None

    world.get_component.side_effect = side_effect

    ctx = evaluator.build_context(world, entity_id)
    assert 'mood' in ctx
    # "Content/Relaxed" logic: Happy >= 0, Stress < 50
    assert ctx['mood'] == "Content/Relaxed"

    # Test expression using mood
    assert evaluator.evaluate("mood == 'Content/Relaxed'", ctx)

def test_caching():
    evaluator = ConditionEvaluator()
    ctx = {"val": 10}

    # Spy on parse
    with patch.object(evaluator.evaluator, 'parse', wraps=evaluator.evaluator.parse) as mock_parse:
        evaluator.evaluate("val > 5", ctx)
        assert mock_parse.call_count == 1

        evaluator.evaluate("val > 5", ctx)
        assert mock_parse.call_count == 1 # Should not increment (hit cache)

        evaluator.evaluate("val < 5", ctx)
        assert mock_parse.call_count == 2 # New expression
