from typing import Dict, Any
import random
from ...engine.ecs import System, World
from ...engine.audio import AudioManager
from ..yukkuri_components import YukkuriStats, AIState
from ..ai.utility import UtilityAIEngine

class DecisionSystem(System):
    """
    System responsible for AI decision making using Utility AI.

    Runs periodically to update the current action of entities.

    Attributes:
        ai_engine (UtilityAIEngine): The UtilityAIEngine instance.
        decision_interval (float): Time in seconds between AI decisions.
        timer (float): Timer to track time since last decision.
    """

    def __init__(self, ai_engine: UtilityAIEngine, decision_interval: float = 1.0):
        """
        Initializes the DecisionSystem.

        Args:
            ai_engine (UtilityAIEngine): The UtilityAIEngine instance.
            decision_interval (float): Time in seconds between AI decisions. Defaults to 1.0.
        """
        self.ai_engine = ai_engine
        self.decision_interval = decision_interval
        self.timer = 0.0

    def update(self, world: World, dt: float) -> None:
        """
        Updates the decision timer and triggers AI decisions.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        self.timer += dt
        if self.timer >= self.decision_interval:
            self.make_decisions(world)
            self.timer = 0.0

    def make_decisions(self, world: World) -> None:
        """
        Runs the utility AI for all eligible entities.

        Args:
            world (World): The ECS World.
        """
        audio = world.services.try_get(AudioManager)
        for entity, (stats, ai) in world.get_components_tuple(YukkuriStats, AIState):
            context = {
                "hunger": stats.hunger,
                "happiness": stats.happiness,
                "happiness_inv": 100 - stats.happiness,
                "cleanliness": stats.cleanliness,
                "energy_inv": 100 - stats.energy,
                "constant_100": 100
            }

            new_action = self.ai_engine.select_action(context)
            if new_action != ai.current_action:
                ai.current_action = new_action
                ai.action_progress = 0.0
                # Reset target if action changes? Not necessarily, behavior tree handles target selection usually.
                # But maybe we should reset it if the new action doesn't use it?
                # For now, keeping behavior identical to original YukkuriAISystem.

            # Randomly trigger a cry if happiness is low or just rarely
            if audio:
                if stats.happiness < 30:
                    if random.random() < 0.1: # 10% chance per decision interval (1 sec)
                         audio.play_sound("cry")
                elif random.random() < 0.01: # 1% chance otherwise
                     audio.play_sound("cry")
