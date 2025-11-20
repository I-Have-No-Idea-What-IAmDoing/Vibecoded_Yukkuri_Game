import random
from typing import List, Any
from src.engine.ecs import System, Entity
from src.engine.components import Transform, Stats, AIComponent, ItemComponent, Identity
from src.utils.loader import game_data

class MovementSystem(System):
    def update(self, delta_time: float, entities: List[Entity], game_state: Any):
        screen_width = game_data.configs["game"]["screen_width"]
        screen_height = game_data.configs["game"]["screen_height"]

        for entity in entities:
            transform = entity.get_component(Transform)
            ai = entity.get_component(AIComponent)

            if not transform:
                continue

            # If performing an action that requires staying still (Eat, Sleep), stop moving
            is_stationary = False
            if ai and ai.current_action:
                action_type = game_data.ai_actions.get(ai.current_action, {}).get("type")
                if action_type in ["survival", "leisure"] and ai.current_action != "wander":
                    is_stationary = True

            if is_stationary:
                transform.vx = 0
                transform.vy = 0
            else:
                # Simple random wander if not targeting
                # In a real game, this would be steering behaviors
                if ai and ai.current_action == "wander":
                    # Randomly change direction occasionally
                    if random.random() < 0.02:
                        speed = 50
                        transform.vx = random.uniform(-speed, speed)
                        transform.vy = random.uniform(-speed, speed)

            # Apply velocity
            transform.x += transform.vx * delta_time
            transform.y += transform.vy * delta_time

            # Bounds checking
            if transform.x < 0:
                transform.x = 0
                transform.vx *= -1
            elif transform.x > screen_width - transform.width:
                transform.x = screen_width - transform.width
                transform.vx *= -1

            if transform.y < 0:
                transform.y = 0
                transform.vy *= -1
            elif transform.y > screen_height - transform.height:
                transform.y = screen_height - transform.height
                transform.vy *= -1

class NeedsSystem(System):
    def update(self, delta_time: float, entities: List[Entity], game_state: Any):
        sim_config = game_data.configs["simulation"]

        for entity in entities:
            stats = entity.get_component(Stats)
            if not stats:
                continue

            # Decay stats
            # Hunger increases
            stats.hunger += sim_config["hunger_decay_rate"] * delta_time
            stats.hunger = min(stats.hunger, stats.max_hunger)

            # Energy decreases
            stats.energy -= sim_config["energy_decay_rate"] * delta_time
            stats.energy = max(0, stats.energy)

            # Happiness decays
            stats.happiness -= sim_config["happiness_decay_rate"] * delta_time
            stats.happiness = max(0, stats.happiness)

            # Cleanliness decays (poop mechanics not fully implemented, but stat exists)
            stats.cleanliness -= 0.1 * delta_time
            stats.cleanliness = max(0, stats.cleanliness)

            # Health logic
            if stats.hunger >= stats.max_hunger:
                stats.health -= 1.0 * delta_time

            if stats.cleanliness <= 0:
                stats.health -= 0.5 * delta_time

            stats.health = max(0, min(stats.max_health, stats.health))

            # Growth
            stats.age += delta_time
            if stats.growth_stage == "Baby" and stats.age > sim_config["growth_threshold_child"]:
                stats.growth_stage = "Child"
            elif stats.growth_stage == "Child" and stats.age > sim_config["growth_threshold_adult"]:
                stats.growth_stage = "Adult"

            # Quality Score Calculation
            # Simple MVP formula
            stats.quality_score = (stats.happiness + stats.health + stats.cleanliness + (stats.badges * 50)) * (1.0 if stats.growth_stage == "Adult" else 0.5)


class InteractionSystem(System):
    def update(self, delta_time: float, entities: List[Entity], game_state: Any):
        # Handle effects of actions

        for entity in entities:
            ai = entity.get_component(AIComponent)
            stats = entity.get_component(Stats)

            if not ai or not stats:
                continue

            if ai.current_action == "eat":
                # For MVP, eating just magically restores hunger without consuming an item object
                # In full version, find closest food and consume it
                stats.hunger -= 10 * delta_time # Restore over time
                stats.hunger = max(0, stats.hunger)

            elif ai.current_action == "sleep":
                stats.energy += 10 * delta_time
                stats.energy = min(stats.max_energy, stats.energy)

            elif ai.current_action == "play":
                stats.happiness += 5 * delta_time
                stats.happiness = min(stats.max_happiness, stats.happiness)

            elif ai.current_action == "talk":
                stats.happiness += 2 * delta_time
                stats.happiness = min(stats.max_happiness, stats.happiness)
                # In a full implementation, this would also increase the partner's happiness

            elif ai.current_action == "breed":
                 # Very basic stub: consume massive energy
                 stats.energy -= 5 * delta_time
                 stats.energy = max(0, stats.energy)

class GameSystems:
    def __init__(self):
        self.movement = MovementSystem()
        self.needs = NeedsSystem()
        self.interaction = InteractionSystem()
