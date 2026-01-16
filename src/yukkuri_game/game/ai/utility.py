"""
Module defining the Utility AI engine and logic.
"""

from dataclasses import dataclass
from typing import Any, Optional
import math
from loguru import logger

# Import TYPE_CHECKING to avoid circular import at runtime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..yukkuri_components import Personality
    from ..trait_service import TraitService


@dataclass
class Consideration:
    """
    A consideration evaluates a single aspect of the world state to produce a score.

    Attributes:
        name (str): The name of the consideration.
        input_key (str): The key to look up in the context dictionary (e.g., "hunger").
        curve_type (str): The type of response curve ("linear", "inverse_linear", "logit", "threshold").
        params (Dict[str, float]): Parameters for the curve function.
    """

    name: str
    input_key: str  # e.g., "hunger", "tiredness"
    curve_type: str  # "linear", "logit", "threshold"
    params: dict[str, float]

    def score(
        self, context: dict[str, Any], override_curve: dict[str, Any] | None = None
    ) -> float:
        """
        Calculates the score for this consideration based on the context.

        Args:
            context (Dict[str, Any]): A dictionary containing the current world state/context.
            override_curve (Optional[Dict[str, Any]]): Optional dictionary with 'curve' and 'params' keys to override the default behavior.

        Returns:
            float: A score between 0.0 and 1.0.
        """
        val = context.get(self.input_key, None)
        if val is None:
            # Log warning only once per key to avoid spam
            if not hasattr(self, "_warned_keys"):
                self._warned_keys = set()
            if self.input_key not in self._warned_keys:
                logger.warning(
                    f"Consideration '{self.name}': Missing context key '{self.input_key}', defaulting to 0.0"
                )
                self._warned_keys.add(self.input_key)
            val = 0.0

        # Check for overrides
        if override_curve:
            return self.evaluate_curve(
                val,
                override_curve.get("curve", self.curve_type),
                override_curve.get("params", self.params),
            )

        return self.evaluate_curve(val, self.curve_type, self.params)

    def evaluate_curve(
        self,
        x: float,
        curve_type: str | None = None,
        params: dict[str, float] | None = None,
    ) -> float:
        """
        Evaluates the configured curve function for a given input value.
        Maps the input value 'x' to a normalized utility score between 0.0 and 1.0.

        Args:
            x (float): The input value.
            curve_type (Optional[str]): The type of curve (optional override).
            params (Optional[Dict[str, float]]): Parameters for the curve (optional override).

        Returns:
            float: The mapped output value between 0.0 and 1.0.
        """
        if curve_type is None:
            curve_type = self.curve_type
        if params is None:
            params = self.params
        # Normalize x usually expected between 0 and 100, map to 0-1 range for easier curve calculation
        v = max(0, min(100, x)) / 100.0

        if curve_type == "linear":
            # Linear mapping: y = mx + b
            m = params.get("m", 1.0)
            b = params.get("b", 0.0)
            return max(0.0, min(1.0, m * v + b))

        elif curve_type == "inverse_linear":
            # High input value results in low score.
            # Useful for things like 'Hunger' where high hunger should drive eating (wait, high hunger = high score needed).
            # If input is 'Satiety', high satiety = low score.
            return 1.0 - v

        elif curve_type == "logit":
            # S-curve (Logistic function). Good for organic behaviors where response ramps up around a midpoint.
            k = params.get("k", 10.0)  # Steepness of the curve
            x0 = params.get("x0", 0.5)  # Midpoint (x-value where y=0.5)
            return 1.0 / (1.0 + math.exp(-k * (v - x0)))

        elif curve_type == "threshold":
            # Binary response: 1.0 if above threshold, else 0.0
            t = params.get("threshold", 0.5)
            return 1.0 if v >= t else 0.0

        return 0.0


@dataclass
class Action:
    """
    An action that an AI agent can perform.

    Attributes:
        name (str): The name of the action.
        considerations (List[Consideration]): A list of considerations that determine the utility of this action.
        weight (float): A base weight multiplier for the action's utility. Defaults to 1.0.
        effects (Optional[Dict[str, Any]]): A dictionary defining the effects of the action.
    """

    name: str
    considerations: list[Consideration]
    weight: float = 1.0
    effects: dict[str, Any] | None = None

    def calculate_utility(
        self, context: dict[str, Any], trait_overrides: dict[str, Any] | None = None
    ) -> float:
        """
        Calculates the total utility score for this action.

        Multiplies the scores of all considerations and the base weight.
        Uses a multiplicative approach so that if any single consideration returns 0,
        the entire action utility becomes 0.

        Args:
            context (Dict[str, Any]): A dictionary containing the current world state/context.
            trait_overrides (Optional[Dict[str, Any]]): A dictionary where keys are consideration names (e.g. "Survival/Eat")
                             and values are override definitions.

        Returns:
            float: The calculated utility score.
        """
        if not self.considerations:
            return 0.0

        final_score = self.weight
        for cons in self.considerations:
            # Check if there is an override for this specific consideration.
            # Overrides allow traits/personalities to modify how a consideration is evaluated
            # (e.g., a "Glutton" trait might make the hunger curve steeper).
            override = trait_overrides.get(cons.name) if trait_overrides else None

            s = cons.score(context, override)
            final_score *= s

            # Optimization: If score drops too low, prune early
            if final_score <= 0.001:
                return 0.0

        return final_score

    def calculate_utility_compensated(
        self, context: dict[str, Any], trait_overrides: dict[str, Any] | None = None
    ) -> float:
        """
        Calculates utility with compensation factor to prevent score collapse.

        Uses geometric mean compensation to address the issue where multiplying
        many small scores together results in a very low final score.
        The formula is: weight * (product of scores) ^ (1/n) where n is the number of considerations.

        Args:
            context: Current world state context.
            trait_overrides: Optional trait modifier overrides.

        Returns:
            float: Compensated utility score.
        """
        if not self.considerations:
            return 0.0

        scores = []
        for cons in self.considerations:
            override = trait_overrides.get(cons.name) if trait_overrides else None
            s = cons.score(context, override)
            if s <= 0.001:
                return 0.0  # Early exit if any consideration fails
            scores.append(s)

        # Geometric mean: (a * b * c) ^ (1/3)
        product = 1.0
        for s in scores:
            product *= s

        compensated = product ** (1.0 / len(scores)) if scores else 0.0
        return self.weight * compensated


class UtilityAIEngine:
    """
    The engine responsible for loading AI actions and selecting the best action based on utility.

    Attributes:
        rm (ResourceManager): The resource manager used to load AI definitions.
        actions (Dict[str, Action]): A dictionary of available actions.
    """

    def __init__(self, resource_manager: Any) -> None:
        """
        Initializes the UtilityAIEngine.

        Args:
            resource_manager (ResourceManager): The ResourceManager instance.
        """
        self.rm = resource_manager
        self.actions: dict[str, Action] = {}
        self.load_actions()

    def load_actions(self) -> None:
        """
        Loads AI actions from the resource manager's loaded data.

        Returns:
            None
        """
        data = self.rm.ai_actions
        for act_name, act_data in data.items():
            self.actions[act_name] = self._parse_action(act_name, act_data)

    def _parse_action(self, name: str, data: Any) -> Action:
        """
        Parses action data (either from dict or msgspec struct) into an Action object.

        Args:
            name (str): The name of the action.
            data (Any): The action data (dict or msgspec struct).

        Returns:
            Action: The parsed Action object.
        """
        considerations = []

        if isinstance(data, dict):
            # Handle dict input
            cons_list = data.get("considerations", [])
            for cons_data in cons_list:
                considerations.append(
                    Consideration(
                        name=cons_data.get("name", "unknown"),
                        input_key=cons_data.get("input"),
                        curve_type=cons_data.get("curve"),
                        params=cons_data.get("params", {}),
                    )
                )

            weight = data.get("weight", 1.0)
            effects = data.get("effects", {})
        else:
            # Handle msgspec struct
            for cons_obj in data.considerations:
                considerations.append(
                    Consideration(
                        name=cons_obj.name,
                        input_key=cons_obj.input,
                        curve_type=cons_obj.curve,
                        params=cons_obj.params,
                    )
                )

            weight = data.weight
            effects = None
            if data.effects:
                effects = {
                    "type": data.effects.type,
                    "target_stat": data.effects.target_stat,
                    "consume": data.effects.consume,
                    "stat_changes": data.effects.stat_changes,
                }

        return Action(
            name=name, considerations=considerations, weight=weight, effects=effects
        )

    def select_action(
        self,
        context: dict[str, Any],
        personality: Optional["Personality"] = None,
        trait_service: Optional["TraitService"] = None,
    ) -> str:
        """
        Selects the action with the highest utility score.

        Args:
            context (Dict[str, Any]): A dictionary containing the current world state/context.
            personality (Optional[Personality]): The personality component of the entity (optional).
            trait_service (Optional[TraitService]): The trait service to look up trait data (optional).

        Returns:
            str: The name of the selected action.
        """
        best_action = "Idle"
        best_score = 0.0

        # Calculate effective overrides if personality exists
        overrides = {}
        # Optimization: Use cached_overrides if available
        if personality and personality.cached_overrides is not None:
            overrides = personality.cached_overrides
        elif personality and trait_service:
            # Fallback if no cache (should generally be cached by selector)
            for trait_id in personality.traits:
                trait_data = trait_service.get_trait(trait_id)
                if trait_data and trait_data.ai_modifiers:
                    # Merge modifiers. If multiple traits modify the same consideration, last one wins (simple approach)
                    # Or we could average/multiply them. For now, last one wins.
                    for cons_name, mod in trait_data.ai_modifiers.items():
                        overrides[cons_name] = mod

        for name, action in self.actions.items():
            # Pass overrides to calculate_utility
            score = action.calculate_utility(context, overrides)
            if score > best_score:
                best_score = score
                best_action = name

        return best_action

    def validate_actions(self) -> None:
        """
        Validates that all loaded utility actions have corresponding implementations
        in the Behavior Tree system. Logs warnings for missing implementations.

        Returns:
            None
        """
        try:
            # Import here to avoid circular dependency
            from .behavior import BehaviorRegistry

            registered_behaviors = BehaviorRegistry.get_goals()

            for action_name in self.actions.keys():
                # Skip validation for Idle as it's the default fallback
                if action_name == "Idle":
                    continue

                if action_name not in registered_behaviors:
                    logger.warning(
                        f"Utility AI Action '{action_name}' defined in actions.toml "
                        f"has no corresponding behavior implementation in BehaviorRegistry."
                    )

        except ImportError:
            logger.error("Could not import BehaviorRegistry for validation.")

    def validate_config(self) -> list[str]:
        """
        Validates the loaded actions configuration for common issues.

        Checks for:
        - Threshold values that may be incorrectly configured (e.g., 1.0 for booleans)
        - Missing weight values
        - Empty considerations

        Returns:
            list[str]: List of warning messages for potential issues.
        """
        warnings = []

        for action_name, action in self.actions.items():
            # Check for empty considerations
            if not action.considerations:
                warnings.append(
                    f"Action '{action_name}': No considerations defined. "
                    "Will always score 0 and never be selected."
                )

            for cons in action.considerations:
                # Check for potentially incorrect threshold values
                if cons.curve_type == "threshold":
                    threshold = cons.params.get("threshold", 0.5)

                    # Warn about thresholds that are too high for boolean inputs
                    if (
                        cons.input_key in ("is_night", "is_predator")
                        and threshold >= 0.5
                    ):
                        warnings.append(
                            f"Action '{action_name}', Consideration '{cons.name}': "
                            f"Threshold {threshold} may be too high for boolean input "
                            f"'{cons.input_key}' (1.0 normalizes to 0.01). "
                            f"Consider using threshold=0.005."
                        )

                    # Warn about thresholds >= 1.0 for count inputs
                    if (
                        cons.input_key in ("nearby_friends", "nearby_enemies")
                        and threshold >= 1.0
                    ):
                        warnings.append(
                            f"Action '{action_name}', Consideration '{cons.name}': "
                            f"Threshold {threshold} is too high for count input "
                            f"'{cons.input_key}' (count of 1 normalizes to 0.01). "
                            f"Consider using threshold=0.01."
                        )

        # Log warnings
        for warning in warnings:
            logger.warning(f"Config Validation: {warning}")

        return warnings

    def debug_score(self, context: dict[str, Any], action_name: str) -> dict[str, Any]:
        """
        Returns detailed scoring breakdown for a specific action.

        Useful for debugging why an action was or wasn't selected.

        Args:
            context: The current context dictionary.
            action_name: Name of the action to debug.

        Returns:
            dict: Detailed breakdown including each consideration's score.
        """
        if action_name not in self.actions:
            return {"error": f"Action '{action_name}' not found"}

        action = self.actions[action_name]
        result: dict[str, Any] = {
            "action": action_name,
            "weight": action.weight,
            "considerations": [],
            "final_score": 0.0,
        }

        if not action.considerations:
            result["final_score"] = 0.0
            result["reason"] = "No considerations"
            return result

        running_score = action.weight
        for cons in action.considerations:
            input_val = context.get(cons.input_key, 0.0)
            normalized_val = max(0, min(100, input_val)) / 100.0
            score = cons.score(context)

            cons_detail = {
                "name": cons.name,
                "input_key": cons.input_key,
                "raw_value": input_val,
                "normalized_value": round(normalized_val, 4),
                "curve": cons.curve_type,
                "params": cons.params,
                "score": round(score, 4),
            }
            result["considerations"].append(cons_detail)
            running_score *= score

        result["final_score"] = round(running_score, 6)
        return result
