import uuid
import random

class Yukkuri:
    def __init__(self, type_data, x, y):
        self.id = str(uuid.uuid4())
        self.type_name = type_data.get('name', 'Unknown')
        self.stats = {
            'health': type_data.get('base_health', 100),
            'hunger': type_data.get('base_hunger', 100),
            'happiness': type_data.get('base_happiness', 100),
            'energy': 100,
            'age': 0
        }
        self.max_stats = {
            'health': type_data.get('base_health', 100),
            'hunger': type_data.get('base_hunger', 100),
            'happiness': type_data.get('base_happiness', 100),
            'energy': 100
        }
        self.decay_rates = {
            'hunger': type_data.get('hunger_decay', 0.5),
            'happiness': type_data.get('happiness_decay', 0.1),
            'energy': 0.3 # Added energy decay
        }
        self.growth_rate = type_data.get('growth_rate', 0.1)
        self.color = type_data.get('color', [255, 255, 255])

        self.position = [x, y]
        self.velocity = [0, 0]
        self.current_action = None
        self.action_target = None # Could be an Item or position

        self.quality_score = 0.0

    def update(self, dt):
        # Decay stats
        self.stats['hunger'] = max(0, self.stats['hunger'] - self.decay_rates['hunger'] * dt)
        self.stats['happiness'] = max(0, self.stats['happiness'] - self.decay_rates['happiness'] * dt)

        # Decay Energy (unless sleeping, which increases it, but that's handled in Action)
        # If we are NOT sleeping (or simply always decay and let sleep overpower it?)
        # Usually simpler to always decay slightly.
        # Sleep action adds +10*dt. Decay is 0.3*dt. Net +9.7. Fine.
        self.stats['energy'] = max(0, self.stats['energy'] - self.decay_rates['energy'] * dt)

        # Age
        self.stats['age'] += self.growth_rate * dt

        # Calculate Quality Score (simplified)
        self.quality_score = (self.stats['health'] + self.stats['happiness'] + self.stats['age']) / 3.0

        # Apply movement if velocity is set
        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt

    def set_action(self, action_name, target=None):
        self.current_action = action_name
        self.action_target = target
        # Reset velocity when changing actions usually, specific actions set velocity
        self.velocity = [0, 0]
