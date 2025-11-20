import random
import math
from typing import Optional
from ...engine.ecs import System, World
from ..components import Transform, Velocity
from ..yukkuri_components import YukkuriStats, AIState, ItemStats
from ..ai.utility import UtilityAIEngine
from ..ai.pathfinding import Pathfinding

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
        yukkuris = world.get_entities_with(YukkuriStats, AIState, Transform)
        items = world.get_entities_with(ItemStats, Transform)

        for entity in yukkuris:
            stats = world.get_component(entity, YukkuriStats)
            ai = world.get_component(entity, AIState)
            trans = world.get_component(entity, Transform)

            if stats and ai and trans:
                # Decay stats
                stats.hunger += 2.0 * dt
                stats.happiness -= 0.5 * dt
                stats.age += dt
                stats.cleanliness -= 0.2 * dt

                # Clamp
                stats.hunger = min(100, max(0, stats.hunger))
                stats.happiness = min(100, max(0, stats.happiness))

                # AI Decision Making
                if self.timer >= self.decision_interval:
                    context = {
                        "hunger": stats.hunger,
                        "happiness": stats.happiness,
                        "happiness_inv": 100 - stats.happiness,
                        "cleanliness": stats.cleanliness,
                        "energy_inv": 0,
                        "constant_100": 100
                    }

                    new_action = self.ai_engine.select_action(context)

                    # If action changed, setup
                    if new_action != ai.current_action:
                        ai.current_action = new_action
                        ai.action_progress = 0.0
                        self.start_action(entity, new_action, world, items)

                # Execute Action
                self.execute_action(entity, ai, trans, world, dt, items)

        if self.timer >= self.decision_interval:
            self.timer = 0.0

    def start_action(self, entity: int, action_name: str, world: World, items: list) -> None:
        """
        Initializes a new action for an entity.

        Sets up targets and paths based on the action type.

        Args:
            entity: The ID of the entity starting the action.
            action_name: The name of the action.
            world: The ECS World.
            items: A list of item entity IDs.
        """
        ai = world.get_component(entity, AIState)
        trans = world.get_component(entity, Transform)

        if not ai or not trans:
            return

        action_def = self.ai_engine.actions.get(action_name)
        if not action_def:
            return

        effects = action_def.effects
        if not effects:
             effects = {}
        action_type = effects.get("type", "idle")

        if action_type == "interact_item":
            target_stat = effects.get("target_stat", "nutrition")
            target = self.find_nearest_item(trans, items, world, target_stat)
            ai.current_target_id = target if target is not None else -1
            ai.path = None

        elif action_type == "move_random":
             # Pick random point
            tx = random.uniform(0, self.world_w)
            ty = random.uniform(0, self.world_h)
            ai.state_data = {"target_x": tx, "target_y": ty}
            ai.path = None

    def execute_action(self, entity: int, ai: AIState, trans: Transform, world: World, dt: float, items: list) -> None:
        """
        Executes the current frame logic for an entity's action.

        Handles movement along paths and interaction with targets.

        Args:
            entity: The ID of the entity.
            ai: The AIState component.
            trans: The Transform component.
            world: The ECS World.
            dt: Delta time.
            items: A list of item entity IDs.
        """
        speed = 100.0 * dt

        action_def = self.ai_engine.actions.get(ai.current_action)
        if not action_def:
            return

        effects = action_def.effects
        if not effects:
             effects = {}
        action_type = effects.get("type", "idle")

        if action_type == "move_random":
            if ai.state_data:
                tx, ty = ai.state_data["target_x"], ai.state_data["target_y"]

                # Pathfinding check
                if ai.path is None:
                    ai.path = Pathfinding.find_path((trans.x, trans.y), (tx, ty), self.world_w, self.world_h)

                self.follow_path(trans, ai, speed)

                if math.hypot(tx - trans.x, ty - trans.y) < 5:
                    ai.current_action = "Idle"
                    ai.path = None

        elif action_type == "interact_item":
            if ai.current_target_id != -1:
                # Check if target still exists
                if not world.has_component(ai.current_target_id, Transform):
                    ai.current_target_id = -1
                    ai.current_action = "Idle"
                    ai.path = None
                    return

                target_trans = world.get_component(ai.current_target_id, Transform)
                if not target_trans:
                     ai.current_target_id = -1
                     ai.current_action = "Idle"
                     ai.path = None
                     return

                # Pathfinding
                if ai.path is None or len(ai.path) == 0:
                     ai.path = Pathfinding.find_path((trans.x, trans.y), (target_trans.x, target_trans.y), self.world_w, self.world_h)

                dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)

                if dist < 20:
                    # Interact
                    item_stats = world.get_component(ai.current_target_id, ItemStats)
                    yukkuri_stats = world.get_component(entity, YukkuriStats)

                    if item_stats:
                        # Apply changes from effects
                        changes = effects.get("stat_changes", {})
                        for stat, val in changes.items():
                            if hasattr(yukkuri_stats, stat):
                                current_val = getattr(yukkuri_stats, stat)
                                setattr(yukkuri_stats, stat, current_val + val)

                    # Consume if needed
                    if effects.get("consume", False):
                        world.destroy_entity(ai.current_target_id)
                        ai.current_target_id = -1
                        ai.current_action = "Idle"
                    else:
                        # Just stay doing it? Or finish?
                        # For Sleep/Play, maybe stay for a while.
                        # For now, finish immediately to keep it simple
                         ai.current_action = "Idle" # Or "Doing"

                    ai.path = None
                else:
                    # Update path target if moving target (not really needed for static items)
                    self.follow_path(trans, ai, speed)
            else:
                ai.current_action = "Wander"

    def follow_path(self, trans: Transform, ai: AIState, speed: float) -> None:
        """
        Moves an entity along its current path.

        Args:
            trans: The entity's Transform component.
            ai: The entity's AIState component.
            speed: The movement distance for this frame.
        """
        if not ai.path:
            return

        # Get next point
        next_point = ai.path[0]
        dist = math.hypot(next_point[0] - trans.x, next_point[1] - trans.y)

        if dist < speed:
            trans.x = next_point[0]
            trans.y = next_point[1]
            ai.path.pop(0)
        else:
            angle = math.atan2(next_point[1] - trans.y, next_point[0] - trans.x)
            trans.x += math.cos(angle) * speed
            trans.y += math.sin(angle) * speed

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
