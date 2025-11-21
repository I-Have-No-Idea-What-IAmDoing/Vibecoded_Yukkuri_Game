import random
import math
from typing import Optional
from ...engine.ecs import System, World
from ..components import Transform, Velocity
from ..yukkuri_components import YukkuriStats, AIState, ItemStats
from ..ai.utility import UtilityAIEngine
from ..ai.pathfinding import Pathfinding
from ..ai.behavior import create_yukkuri_behavior_tree
import py_trees

class YukkuriAISystem(System):
    """
    System responsible for simulating Yukkuri behavior and stats.

    Handles stats decay, decision making via Utility AI, and action execution (movement, interaction).

    Attributes:
        ai_engine (UtilityAIEngine): The AI engine used for decision making.
        timer (float): Timer for controlling decision frequency.
        decision_interval (float): Time in seconds between AI decisions.
        world_w (float): Width of the world for random movement.
        world_h (float): Height of the world for random movement.
        trees (dict): A dictionary mapping entity IDs to their behavior trees.
    """

    def __init__(self, ai_engine: UtilityAIEngine, world_width: float, world_height: float):
        """
        Initializes the YukkuriAISystem.

        Args:
            ai_engine: The UtilityAIEngine instance.
            world_width: The width of the world.
            world_height: The height of the world.
        """
        self.ai_engine = ai_engine
        self.timer = 0.0
        self.decision_interval = 1.0
        self.world_w = world_width
        self.world_h = world_height
        self.trees = {}

    def update(self, world: World, dt: float) -> None:
        """
        Updates the simulation.

        Decays stats, triggers AI decisions, and executes current actions.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        self.timer += dt

        # Update Yukkuri Stats (Needs, Growth)
        # Optimized iteration using tuple unpacking
        for entity, (stats, ai, trans) in world.get_components_tuple(YukkuriStats, AIState, Transform):
                # Decay stats
                stats.hunger += 2.0 * dt
                stats.happiness -= 0.5 * dt
                stats.energy -= 0.5 * dt
                stats.age += dt
                stats.cleanliness -= 0.2 * dt

                # Clamp
                stats.hunger = min(100, max(0, stats.hunger))
                stats.happiness = min(100, max(0, stats.happiness))
                stats.energy = min(100, max(0, stats.energy))

                # AI Decision Making
                if self.timer >= self.decision_interval:
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
                        # We don't need start_action anymore as BT handles it, or we keep it for initialization

                # Create BT if not exists
                if entity not in self.trees:
                    self.trees[entity] = create_yukkuri_behavior_tree(entity, world, self.world_w, self.world_h)
                    self.trees[entity].setup(timeout=15)

                # Set dt in Blackboard
                py_trees.blackboard.Blackboard().set("dt", dt)

                # Tick Behavior Tree
                self.trees[entity].tick_once()

        if self.timer >= self.decision_interval:
            self.timer = 0.0

    def find_nearest_item(self, trans: Transform, items: list, world: World, stat_check: str) -> Optional[int]:
        """
        Finds the nearest item that satisfies a specific stat requirement.

        Args:
            trans: The position of the seeker.
            items: A list of item entity IDs.
            world: The ECS World.
            stat_check: The name of the stat the item must have (e.g., "nutrition").

        Returns:
            Optional[int]: The ID of the nearest matching item, or None if none found.
        """
        best_dist = float('inf')
        best_item = None

        for item in items:
            istats = world.get_component(item, ItemStats)
            itrans = world.get_component(item, Transform)

            if not istats or not itrans:
                continue

            # Check if item provides the stat
            val = getattr(istats, stat_check, 0)
            if val > 0:
                dist = math.hypot(itrans.x - trans.x, itrans.y - trans.y)
                if dist < best_dist:
                    best_dist = dist
                    best_item = item
        return best_item
