from src.ai.considerations import Considerations
from src.ai.actions import Actions

class UtilityAIEngine:
    def __init__(self, data_loader):
        self.data_loader = data_loader

    def update(self, yukkuri, yukkurrium, dt):
        # If currently doing an action that shouldn't be interrupted, continue
        if yukkuri.current_action:
            # Execute current action
            self.execute_action(yukkuri.current_action, yukkuri, yukkurrium, dt)
            return

        # Evaluate all actions
        best_action = None
        best_score = -float('inf')

        for action_name, action_data in self.data_loader.ai_actions.items():
            score = self.calculate_utility(yukkuri, action_data)
            if score > best_score:
                best_score = score
                best_action = action_name

        if best_action:
            yukkuri.set_action(best_action)

    def calculate_utility(self, yukkuri, action_data):
        base_score = action_data.get('base_score', 0)
        considerations = action_data.get('considerations', [])

        # If no considerations, rely ONLY on base_score (don't add the 100 factor)
        if not considerations:
            return base_score

        factor = 1.0

        for cons in considerations:
            input_key = cons.get('input')
            val = 0

            # Considerations Logic
            # Hunger: Stored as Fullness (100->0). We invert to represent Need (0->100).
            if input_key == 'hunger': val = 100 - yukkuri.stats['hunger']
            elif input_key == 'energy': val = yukkuri.stats['energy'] # Sleep Action uses Inverse Linear so Low Energy -> High Score
            elif input_key == 'happiness': val = yukkuri.stats['happiness']

            score = Considerations.evaluate(val, cons)
            factor *= score

        return base_score + (factor * 100)

    def execute_action(self, action_name, yukkuri, yukkurrium, dt):
        method_name = f"execute_{action_name.lower()}"
        if hasattr(Actions, method_name):
            getattr(Actions, method_name)(yukkuri, yukkurrium, dt)
        else:
            yukkuri.current_action = None
