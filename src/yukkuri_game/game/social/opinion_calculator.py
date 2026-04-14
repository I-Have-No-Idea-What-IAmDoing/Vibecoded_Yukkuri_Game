"""
Opinion Calculator - Pure Logic for Social Math.

Extracts the mathematical logic for calculating compatibility,
interaction impacts, and emotional updates from the SocialSystem.
"""

from typing import Any, cast

from ...engine.ecs import World
from ..utils.evaluator import ConditionEvaluator
from ..yukkuri_components import EmotionalState, Personality
from ..trait_service import TraitService


class OpinionCalculator:
    """Stateless calculator for social opinion math.

    Provides pure logic methods for computing compatibility between entities,
    evaluating the impact of social interactions, and updating emotional states.
    All methods are static and do not maintain internal state.
    """

    BASE_COMPATIBILITY_SCORE = 100.0
    COMPATIBILITY_DIVISOR = 4.0
    IMPACT_THRESHOLD_MAJOR_NEGATIVE = -15.0
    IMPACT_THRESHOLD_MAJOR_POSITIVE = 15.0
    EMOTIONAL_CHANGE_AMOUNT = 20.0
    MAX_HAPPINESS = 100.0
    MIN_HAPPINESS = -100.0
    MAX_STRESS = 100.0
    MIN_STRESS = 0.0

    @staticmethod
    def calculate_base_compatibility(
        subject_pers: Personality,
        other_pers: Personality,
        trait_service: TraitService | None,
    ) -> float:
        """Calculates base compatibility between two personalities.

        Computes a compatibility score by comparing the differences across four
        personality axes (kindness, energy, bravery, greed) and applying trait-based
        modifiers if a TraitService is provided.

        Args:
            subject_pers: The personality component of the evaluating entity.
            other_pers: The personality component of the target entity.
            trait_service: The service used to retrieve trait definitions and social modifiers.

        Returns:
            The calculated base compatibility score as a float.
        """
        base_compatibility = 0.0

        if subject_pers.axis and other_pers.axis:
            diff_kind = abs(subject_pers.axis.kindness - other_pers.axis.kindness)
            diff_ener = abs(subject_pers.axis.energy - other_pers.axis.energy)
            diff_brav = abs(subject_pers.axis.bravery - other_pers.axis.bravery)
            diff_gree = abs(subject_pers.axis.greed - other_pers.axis.greed)

            total_diff = diff_kind + diff_ener + diff_brav + diff_gree
            base_compatibility += OpinionCalculator.BASE_COMPATIBILITY_SCORE - (
                total_diff / OpinionCalculator.COMPATIBILITY_DIVISOR
            )

        if trait_service:
            for my_trait in subject_pers.traits:
                trait_data = trait_service.get_trait(my_trait)
                if not trait_data:
                    continue

                if isinstance(trait_data, dict):
                    td_dict = cast(dict[str, Any], trait_data)
                    social_mods = td_dict.get("social_modifiers", {})
                else:
                    social_mods = getattr(trait_data, "social_modifiers", {})

                if "compatibility" not in social_mods:
                    continue

                comp_map = social_mods["compatibility"]
                for other_trait in other_pers.traits:
                    if other_trait in comp_map:
                        base_compatibility += comp_map[other_trait]

        return base_compatibility

    @staticmethod
    def calculate_impact_deltas(
        world: World,
        subject_id: int,
        other_id: int,
        social_impact: dict[str, float],
        modifiers: dict[str, dict[str, float]],
        base_impact_score: float,
    ) -> tuple[float, float, float, float]:
        """Calculates impact deltas considering personality and traits.

        Evaluates the base social impact of an interaction and adjusts it based on
        the subject's traits, conditional modifiers evaluated via ConditionEvaluator,
        and personality axis multipliers.

        Args:
            world: The active ECS world containing entity data.
            subject_id: The entity ID of the subject processing the impact.
            other_id: The entity ID of the target involved in the interaction.
            social_impact: Base impact values for affinity, trust, fear, and familiarity.
            modifiers: Additional conditional or trait-based modifiers to apply.
            base_impact_score: The net score determining whether the interaction is positive or negative.

        Returns:
            A tuple containing delta values for (affinity, trust, fear, familiarity).
        """
        d_affinity = social_impact.get("affinity", 0.0)
        d_trust = social_impact.get("trust", 0.0)
        d_fear = social_impact.get("fear", 0.0)
        d_familiarity = social_impact.get("familiarity", 0.0)

        subject_personality = world.get_component(subject_id, Personality)
        if subject_personality:
            for trait in subject_personality.traits:
                key = f"trait:{trait}"
                if key in modifiers:
                    mod = modifiers[key]
                    d_affinity += mod.get("affinity", 0.0)
                    d_trust += mod.get("trust", 0.0)
                    d_fear += mod.get("fear", 0.0)

            evaluator = world.services.try_get(ConditionEvaluator)
            if evaluator:
                actor_context = evaluator.build_context(world, other_id)
                for key, mod in modifiers.items():
                    if key.startswith("trait:") or key.startswith("mood:"):
                        continue

                    if evaluator.evaluate(key, actor_context):
                        d_affinity += mod.get("affinity", 0.0)
                        d_trust += mod.get("trust", 0.0)
                        d_fear += mod.get("fear", 0.0)

            # Kindness scales the impact magnitude: high kindness amplifies positive impacts and mitigates negative impacts.
            kindness = 0
            if subject_personality.axis:
                kindness = subject_personality.axis.kindness

            if base_impact_score > 0:
                comp_mult = max(0.1, 1.0 + (kindness / 100.0))
                d_affinity *= comp_mult
                d_trust *= comp_mult
            elif base_impact_score < 0:
                comp_mult = max(0.1, 1.0 - (kindness / 100.0))
                d_affinity *= comp_mult
                d_trust *= comp_mult
                d_fear *= comp_mult

        return d_affinity, d_trust, d_fear, d_familiarity

    @staticmethod
    def update_emotional_state(
        emotional: EmotionalState, base_impact_score: float
    ) -> None:
        """Updates emotional state based on interaction impact.

        Mutates the passed EmotionalState component directly. Increases stress and
        decreases happiness on major negative impacts, while increasing happiness
        on major positive impacts. Clamps values to predefined bounds.

        Args:
            emotional: The emotional state component to mutate.
            base_impact_score: The calculated score representing the interaction's severity.
        """
        if base_impact_score < OpinionCalculator.IMPACT_THRESHOLD_MAJOR_NEGATIVE:
            emotional.happiness = max(
                OpinionCalculator.MIN_HAPPINESS,
                emotional.happiness - OpinionCalculator.EMOTIONAL_CHANGE_AMOUNT,
            )
            emotional.stress = min(
                OpinionCalculator.MAX_STRESS,
                emotional.stress + OpinionCalculator.EMOTIONAL_CHANGE_AMOUNT,
            )
        elif base_impact_score > OpinionCalculator.IMPACT_THRESHOLD_MAJOR_POSITIVE:
            emotional.happiness = min(
                OpinionCalculator.MAX_HAPPINESS,
                emotional.happiness + OpinionCalculator.EMOTIONAL_CHANGE_AMOUNT,
            )
