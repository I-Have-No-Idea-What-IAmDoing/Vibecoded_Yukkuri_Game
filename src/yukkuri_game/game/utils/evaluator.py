from typing import Any, Dict, Optional, Type
from simpleeval import SimpleEval
from loguru import logger
from ...engine.ecs import World
from ..yukkuri_components import YukkuriStats, Needs, EmotionalState, Skills, Personality

class ConditionEvaluator:
    def __init__(self) -> None:
        self.evaluator = SimpleEval()
        self._cache: Dict[str, Any] = {}

        def has_trait(trait: str) -> bool:
            # Access traits from the current evaluation context
            traits = self.evaluator.names.get('traits', [])
            if traits is None:
                return False
            return trait in traits

        # Register custom safe functions if needed
        self.evaluator.functions = {
            "min": min,
            "max": max,
            "has_trait": has_trait
        }

    def build_context(self, world: World, entity_id: int) -> Dict[str, Any]:
        """Builds a flat data context for an entity."""
        context: Dict[str, Any] = {}

        # Stats
        stats = world.get_component(entity_id, YukkuriStats)
        if stats:
            context['discipline'] = stats.discipline
            context['age'] = stats.age
            context['intelligence'] = stats.intelligence

        # Needs
        needs = world.get_component(entity_id, Needs)
        if needs:
            context['health'] = needs.health
            context['hunger'] = needs.hunger
            context['stress'] = 0.0 # Default if emotion missing
            context['energy'] = needs.energy
            context['cleanliness'] = needs.cleanliness
            context['bladder'] = needs.bladder
            context['easiness'] = needs.easiness

        # Personality (Fetch first to use for mood)
        pers = world.get_component(entity_id, Personality)
        if pers:
            context['traits'] = list(pers.traits)
            if pers.axis:
                context['kindness'] = pers.axis.kindness
                context['greed'] = pers.axis.greed
                context['energy_axis'] = pers.axis.energy
                context['bravery'] = pers.axis.bravery

        # Emotion
        emotion = world.get_component(entity_id, EmotionalState)
        if emotion:
            context['happiness'] = emotion.happiness
            context['stress'] = emotion.stress

            # Inject Mood
            bravery = 0
            if pers and pers.axis:
                 bravery = pers.axis.bravery
            context['mood'] = emotion.get_dominant_emotion(bravery)

        # Skills (Flattened for easy access: skills.athletics)
        skills = world.get_component(entity_id, Skills)
        skill_map: Dict[str, int] = {}
        if skills:
            for s_id, s_state in skills.states.items():
                skill_map[s_id] = s_state.level
        context['skills'] = skill_map

        return context

    def evaluate(self, expression: str, context: Dict[str, Any], expected_type: Type = bool) -> bool:
        """
        Evaluates a boolean expression string.

        Args:
            expression (str): The expression to evaluate.
            context (Dict[str, Any]): The variables available to the expression.
            expected_type (Type): The expected return type (default bool). Logs warning if mismatched.

        Returns:
            bool: The result of the evaluation, coerced to bool.
        """
        self.evaluator.names = context
        try:
            # Check cache
            if expression not in self._cache:
                node = self.evaluator.parse(expression)
                # Unwrap ast.Expr if needed
                if hasattr(node, 'value'):
                    node = node.value
                self._cache[expression] = node

            cached_node = self._cache[expression]

            # Use internal _eval with cached AST
            # Note: _eval takes (node) and uses self.names
            result = self.evaluator._eval(cached_node)

            if expected_type is bool and not isinstance(result, bool):
                 # Log warning for type mismatch, but proceed with implicit conversion
                 logger.warning(f"Expression '{expression}' evaluated to {type(result).__name__} ({result}) instead of bool.")

            return bool(result)
        except Exception as e:
            # Fallback for bad data/expressions to prevent crash
            logger.warning(f"Expression evaluation error: '{expression}' - {e}")
            return bool(False)
