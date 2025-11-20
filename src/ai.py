import math
from .config import load_config

class UtilityCurve:
    """Represents a curve that maps an input value to a utility score (0-1)."""
    def __init__(self, curve_type="linear", params=None):
        self.curve_type = curve_type
        self.params = params if params else {}

    def get_score(self, value):
        """Calculates the utility score based on the curve type."""
        if self.curve_type == "linear":
            m = self.params.get("m", 1)
            b = self.params.get("b", 0)
            return max(0, min(1, m * value + b))
        elif self.curve_type == "quadratic":
            a = self.params.get("a", 1)
            b = self.params.get("b", 0)
            c = self.params.get("c", 0)
            return max(0, min(1, a * value**2 + b * value + c))
        # Add more curve types as needed
        return 0.0

class Consideration:
    """A factor that influences the utility of an action."""
    def __init__(self, name, curve):
        self.name = name
        self.curve = curve

    def get_score(self, yukkuri_state):
        """Gets the utility score for this consideration."""
        value = yukkuri_state.get(self.name, 0)
        return self.curve.get_score(value)

class Action:
    """A possible action a Yukkuri can take."""
    def __init__(self, name, considerations):
        self.name = name
        self.considerations = considerations

    def get_score(self, yukkuri_state):
        """Calculates the final utility score for this action."""
        # Simple averaging for now
        if not self.considerations:
            return 0.0
        total_score = sum(c.get_score(yukkuri_state) for c in self.considerations)
        return total_score / len(self.considerations)

class UtilityAIEngine:
    """Manages the AI for all Yukkuris."""
    def __init__(self, ai_config_path="data/ai_config.toml"):
        self.actions = {}
        self.load_actions(ai_config_path)

    def load_actions(self, file_path):
        """Loads AI actions, considerations, and curves from a config file."""
        config = load_config(file_path)
        if not config:
            return

        for action_name, action_data in config.items():
            considerations = []
            for cons_name, cons_data in action_data.get("considerations", {}).items():
                curve_type = cons_data.get("curve", "linear")
                params = cons_data.get("params", {})
                curve = UtilityCurve(curve_type, params)
                considerations.append(Consideration(cons_name, curve))
            self.actions[action_name] = Action(action_name, considerations)

    def select_action(self, yukkuri):
        """Selects the best action for a Yukkuri based on utility scores."""
        best_action = None
        best_score = -1
        yukkuri_state = yukkuri.get_state()

        for action_name, action in self.actions.items():
            score = action.get_score(yukkuri_state)
            if score > best_score:
                best_score = score
                best_action = action_name

        return best_action
