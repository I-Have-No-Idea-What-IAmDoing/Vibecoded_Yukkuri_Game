"""
Module defining the ConditionEvaluator for dynamic expression parsing.
"""

from typing import Any
from simpleeval import SimpleEval  # type: ignore[import-untyped]
from loguru import logger
from ...engine.ecs import World
from ..yukkuri_components import (
    YukkuriStats,
    Needs,
    EmotionalState,
    Skills,
    Personality,
)


class ConditionEvaluator:
    """
    Evaluates condition strings using SimpleEval.
    Provides a safe environment to check entity state (stats, traits, skills).

    Attributes:
        evaluator (SimpleEval): The expression evaluator engine.
        _cache (Dict[str, Any]): Cache for compiled expression ASTs to improve performance.
    """

    def __init__(self) -> None:
        """Initializes the ConditionEvaluator."""
        self.evaluator = SimpleEval()
        self._cache: dict[str, Any] = {}

        def has_trait(trait: str) -> bool:
            """
            Checks if the 'traits' list in context contains the given trait.

            Args:
                trait (str): The trait to check for.

            Returns:
                bool: True if the trait is present, False otherwise.
            """
            # Access traits from the current evaluation context
            traits = self.evaluator.names.get("traits", [])
            if traits is None or isinstance(traits, bool):
                return False
            return trait in traits

        # Register custom safe functions if needed
        self.evaluator.functions = {"min": min, "max": max, "has_trait": has_trait}

    def build_context(self, world: World, entity_id: int) -> dict[str, Any]:
        """
        Builds a flat data context for an entity suitable for expression evaluation.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity ID.

        Returns:
            Dict[str, Any]: The context dictionary containing stats, needs, etc.
        """
        context: dict[str, Any] = {}

        # Stats
        stats = world.get_component(entity_id, YukkuriStats)
        if stats:
            context["discipline"] = stats.discipline
            context["age"] = stats.age
            context["intelligence"] = stats.intelligence

        # Needs
        needs = world.get_component(entity_id, Needs)
        if needs:
            context["health"] = needs.health
            context["hunger"] = needs.hunger
            context["stress"] = 0.0  # Default if emotion missing
            context["energy"] = needs.energy
            context["cleanliness"] = needs.cleanliness
            context["bladder"] = needs.bladder
            context["easiness"] = needs.easiness

        # Personality (Fetch first to use for mood)
        pers = world.get_component(entity_id, Personality)
        if pers:
            context["traits"] = list(pers.traits)
            if pers.axis:
                context["kindness"] = pers.axis.kindness
                context["greed"] = pers.axis.greed
                context["energy_axis"] = pers.axis.energy
                context["bravery"] = pers.axis.bravery

        # Emotion
        emotion = world.get_component(entity_id, EmotionalState)
        if emotion:
            context["happiness"] = emotion.happiness
            context["stress"] = emotion.stress

            # Inject Mood
            bravery = 0
            if pers and pers.axis:
                bravery = pers.axis.bravery
            context["mood"] = emotion.get_dominant_emotion(bravery)

        # Skills (Flattened for easy access: skills.athletics)
        skills = world.get_component(entity_id, Skills)
        skill_map: dict[str, int] = {}
        if skills:
            for s_id, s_state in skills.states.items():
                skill_map[s_id] = s_state.level
        context["skills"] = skill_map

        return context

    def evaluate(
        self, expression: str, context: dict[str, Any], expected_type: type = bool
    ) -> bool:
        """
        Evaluates a boolean expression string against a given context.

        Args:
            expression (str): The expression string (e.g., "hunger > 50 and not has_trait('Stoic')").
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
                if hasattr(node, "value"):
                    node = node.value
                self._cache[expression] = node

            cached_node = self._cache[expression]

            # Use internal _eval with cached AST
            # Note: _eval takes (node) and uses self.names
            # We use _eval because simpleeval does not expose a public method to evaluate a pre-parsed AST node.
            # This is safe as long as we are careful with the AST generation (which we do via evaluator.parse).
            result = self.evaluator._eval(cached_node)

            if expected_type is bool and not isinstance(result, bool):
                # Log warning for type mismatch, but proceed with implicit conversion
                logger.warning(
                    f"Expression '{expression}' evaluated to {type(result).__name__} ({result}) instead of bool."
                )

            return bool(result)
        except Exception as e:
            # Fallback for bad data/expressions to prevent crash
            logger.warning(f"Expression evaluation error: '{expression}' - {e}")
            return False
