from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Optional, Union
import math
from loguru import logger

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
    curve_type: str # "linear", "logit", "threshold"
    params: Dict[str, float]

    def score(self, context: Dict[str, Any], override_curve: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculates the score for this consideration based on the context.

        Args:
            context: A dictionary containing the current world state/context.
            override_curve: Optional curve override configuration.

        Returns:
            float: A score between 0.0 and 1.0.
        """
        val = context.get(self.input_key, 0.0)

        curve = self.curve_type
        params = self.params

        if override_curve:
            curve = override_curve.get("curve", curve)
            params = override_curve.get("params", params)

        return self.evaluate_curve(val, curve, params)

    def evaluate_curve(self, x: float, curve_type: str, params: Dict[str, float]) -> float:
        """
        Evaluates the configured curve function for a given input value.

        Args:
            x: The input value.
            curve_type: The type of curve.
            params: Parameters for the curve.

        Returns:
            float: The mapped output value between 0.0 and 1.0.
        """
        # Normalize x usually expected between 0 and 100, map to 0-1
        v = max(0, min(100, x)) / 100.0

        if curve_type == "linear":
            m = params.get("m", 1.0)
            b = params.get("b", 0.0)
            return max(0.0, min(1.0, m * v + b))

        elif curve_type == "inverse_linear":
            # High value = low score
            return 1.0 - v

        elif curve_type == "logit":
            # S-curve
            k = params.get("k", 10.0) # Steepness
            x0 = params.get("x0", 0.5) # Midpoint
            return 1.0 / (1.0 + math.exp(-k * (v - x0)))

        elif curve_type == "threshold":
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
    considerations: List[Consideration]
    weight: float = 1.0
    effects: Optional[Dict[str, Any]] = None

    def calculate_utility(self, context: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculates the total utility score for this action.

        Multiplies the scores of all considerations and the base weight.

        Args:
            context: A dictionary containing the current world state/context.
            overrides: Optional dictionary of consideration overrides (name -> curve config).

        Returns:
            float: The calculated utility score.
        """
        if not self.considerations:
            return 0.0

        final_score = self.weight
        for cons in self.considerations:
            # Check for override
            override_curve = None
            if overrides:
                # Assuming override key matches consideration name
                override_curve = overrides.get(cons.name)

            s = cons.score(context, override_curve)
            final_score *= s

            if final_score <= 0.001:
                return 0.0

        return final_score

class UtilityAIEngine:
    """
    The engine responsible for loading AI actions and selecting the best action based on utility.

    Attributes:
        rm (ResourceManager): The resource manager used to load AI definitions.
        actions (Dict[str, Action]): A dictionary of available actions.
    """

    def __init__(self, resource_manager: Any, trait_service: Optional['TraitService'] = None) -> None:
        """
        Initializes the UtilityAIEngine.

        Args:
            resource_manager: The ResourceManager instance.
            trait_service: The TraitService instance.
        """
        self.rm = resource_manager
        self.trait_service = trait_service
        self.actions: Dict[str, Action] = {}
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
            name: The name of the action.
            data: The action data (dict or msgspec struct).

        Returns:
            Action: The parsed Action object.
        """
        considerations = []

        if isinstance(data, dict):
            # Handle dict input
            cons_list = data.get("considerations", [])
            for cons_data in cons_list:
                considerations.append(Consideration(
                    name=cons_data.get("name", "unknown"),
                    input_key=cons_data.get("input"),
                    curve_type=cons_data.get("curve"),
                    params=cons_data.get("params", {})
                ))

            weight = data.get("weight", 1.0)
            effects = data.get("effects", {})
        else:
            # Handle msgspec struct
            for cons_obj in data.considerations:
                considerations.append(Consideration(
                    name=cons_obj.name,
                    input_key=cons_obj.input,
                    curve_type=cons_obj.curve,
                    params=cons_obj.params
                ))

            weight = data.weight
            effects = None
            if data.effects:
                effects = {
                    "type": data.effects.type,
                    "target_stat": data.effects.target_stat,
                    "consume": data.effects.consume,
                    "stat_changes": data.effects.stat_changes
                }

        return Action(
            name=name,
            considerations=considerations,
            weight=weight,
            effects=effects
        )

    def select_action(self, context: Dict[str, Any], personality: Optional['Personality'] = None) -> str:
        """
        Selects the action with the highest utility score.

        Args:
            context: A dictionary containing the current world state/context.
            personality: The personality component of the entity (optional).

        Returns:
            str: The name of the selected action.
        """
        best_action = "Idle"
        best_score = 0.0

        # Gather overrides from traits
        overrides = {}
        if personality and self.trait_service:
            for trait_id in personality.traits:
                trait_data = self.trait_service.get_trait(trait_id)
                if trait_data:
                    ai_mods = trait_data.get("ai_modifiers", {})
                    # Merge ai_mods into overrides
                    # If multiple traits modify the same thing, last one wins (or implement priority/blend)
                    overrides.update(ai_mods)

        for name, action in self.actions.items():
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
