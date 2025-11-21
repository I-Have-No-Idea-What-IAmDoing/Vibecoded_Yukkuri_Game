import py_trees
import math
import random
from typing import Optional, Callable, Any, TYPE_CHECKING
from py_trees.behaviour import Behaviour
from py_trees.common import Status
from typing import Optional, Callable, Any, TYPE_CHECKING, Dict
from ..components import Transform, PhysicsBody, Velocity
from ..yukkuri_components import AIState, ItemStats, YukkuriStats
from .utility_selector import UtilitySelector
from .base_action import Action
from ..ai.pathfinding import Pathfinding
from ..services import GameService

if TYPE_CHECKING:
    from ..config import GameConfig
    from yukkuri_game.engine.ecs import World

# --- Behavior Tree Leaves (Actions) ---

class MoveToTarget(Action):
    """
    Moves the entity towards the current target set in AIState or a specific coordinate.

    This implementation uses PhysicsBody if available, or direct Transform manipulation.

    Attributes:
        speed (float): The movement speed in pixels per second.
    """
    def __init__(self, name: str = "Move To Target", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None, speed: float = 100.0):
        """
        Initializes the MoveToTarget action.

        Args:
            name (str): The name of the behavior node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World instance.
            blackboard (Optional[Any]): The Behavior Tree blackboard.
            speed (float): The movement speed in pixels per second.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.speed = speed

    def update(self) -> Status:
        """
        Updates the movement logic.

        Calculates the direction to the target, applies velocity or transform changes,
        and handles pathfinding along waypoints.

        Returns:
            Status: RUNNING if moving, SUCCESS if reached target, FAILURE if target lost or unreachable.
        """
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)
        phys = self.world.get_component(self.entity_id, PhysicsBody)

        if not ai or not trans:
            return Status.FAILURE

        target_pos = None

        # Determine target position
        if ai.current_target_id != -1:
            target_trans = self.world.get_component(ai.current_target_id, Transform)
            if target_trans:
                target_pos = (target_trans.x, target_trans.y)
            else:
                # Target lost
                ai.current_target_id = -1
                return Status.FAILURE
        elif ai.state_data and "target_x" in ai.state_data and "target_y" in ai.state_data:
            target_pos = (ai.state_data["target_x"], ai.state_data["target_y"])

        if target_pos is None:
            return Status.FAILURE

        # Pathfinding
        if ai.path is None or len(ai.path) == 0:
             # Simple check to see if we need pathfinding or just straight line
             # For now, assuming pathfinding is always needed or available
             # Check if we are already at the target before calling pathfinding
             if math.hypot(target_pos[0] - trans.x, target_pos[1] - trans.y) < 15.0:
                 return Status.SUCCESS

             game_config = self.world.services.try_get(GameConfig)
             world_width = 3000
             world_height = 3000
             grid_step_size = 50

             if game_config:
                 world_width = game_config.world.width
                 world_height = game_config.world.height
                 grid_step_size = game_config.world.grid_step_size

             ai.path = Pathfinding.find_path((trans.x, trans.y), target_pos, world_width, world_height, grid_step_size)
             if not ai.path:
                 return Status.FAILURE

        # Move along path
        if len(ai.path) > 0:
            next_point = ai.path[0]
            dx = next_point[0] - trans.x
            dy = next_point[1] - trans.y
            dist = math.hypot(dx, dy)

            # Check if we are close to the *final* target
            dist_to_final = math.hypot(target_pos[0] - trans.x, target_pos[1] - trans.y)
            # Use a threshold slightly smaller than the interaction range to ensure we are close enough to interact
            if dist_to_final < 15.0:
                ai.path = []
                return Status.SUCCESS

            if dist < 5.0: # Reached waypoint
                ai.path.pop(0)
                if not ai.path: # Reached end of path
                    return Status.SUCCESS
            else:
                # Normalize direction
                dx /= dist
                dy /= dist

                # Apply movement
                if phys:
                    # Use physics velocity
                    phys.body.velocity = (dx * self.speed, dy * self.speed)
                    # Wake up body just in case
                    phys.body.activate()
                else:
                    # Fallback to direct transform manipulation
                    # We read delta time from blackboard if available
                    dt = py_trees.blackboard.Blackboard().get("dt")
                    # Check if dt is None or invalid
                    if dt is None:
                         dt = 0.016 # Fallback to ~60FPS

                    step = self.speed * float(dt)
                    if step > dist:
                        trans.x = next_point[0]
                        trans.y = next_point[1]
                    else:
                        trans.x += dx * step
                        trans.y += dy * step

            return Status.RUNNING

        return Status.SUCCESS

class Wander(Action):
    """
    Causes the entity to wander to a random location.

    Attributes:
        width (int): The width of the area to wander within.
        height (int): The height of the area to wander within.
        move_action (Optional[MoveToTarget]): The underlying move action used to reach the random target.
    """
    def __init__(self, name: str = "Wander", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None, width: int = 3000, height: int = 3000):
        """
        Initializes the Wander action.

        Args:
            name (str): The name of the behavior node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World instance.
            blackboard (Optional[Any]): The Behavior Tree blackboard.
            width (int): The width of the area to wander within.
            height (int): The height of the area to wander within.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.width = width
        self.height = height
        self.move_action: Optional[MoveToTarget] = None

    def initialise(self) -> None:
        """
        Selects a random target location and initializes the move action.
        """
        if self.world is None or self.entity_id is None:
            return

        ai = self.world.get_component(self.entity_id, AIState)
        if ai:
            # Pick a random point
            tx = random.uniform(0, self.width)
            ty = random.uniform(0, self.height)
            ai.state_data = {"target_x": tx, "target_y": ty}
            ai.path = None # Reset path

        # Create a temporary MoveToTarget to handle the actual movement logic
        self.move_action = MoveToTarget(entity_id=self.entity_id, world=self.world, blackboard=self.blackboard)

    def update(self) -> Status:
        """
        Updates the move action.

        Returns:
            Status: The status of the move action (RUNNING, SUCCESS, FAILURE).
        """
        if self.move_action:
            return self.move_action.update()
        return Status.FAILURE

class Interact(Action):
    """
    Handles interaction with a target entity (e.g., eating food).
    """
    def __init__(self, name: str = "Interact", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None, consume: bool = True):
        """
        Initializes the Interact action.

        Args:
            name (str): The name of the behavior node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World instance.
            blackboard (Optional[Any]): The Behavior Tree blackboard.
            consume (bool): Whether the interaction should consume the target.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.consume = consume

    def update(self) -> Status:
        """
        Checks distance to target and performs interaction if close enough.

        Returns:
            Status: SUCCESS if interaction complete, RUNNING if waiting/moving closer (though MoveToTarget handles moving), FAILURE if target invalid.
        """
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
            return Status.FAILURE

        if ai.current_target_id == -1:
            # If target lost or not set, check if we can find it again locally or fail
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if not target_trans:
            # print("Interact Fail: Target trans missing")
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        # print(f"Interact Check: Dist={dist}")
        if dist <= 30.0: # Interaction range
            game_service = self.world.services.try_get(GameService)
            if game_service:
                # Use GameService to handle consumption
                success = game_service.interact_with_item(self.entity_id, ai.current_target_id, self.consume)
                return Status.SUCCESS if success else Status.FAILURE
            else:
                # Fallback if GameService is missing (though it should be there)
                # This logic was previously in execute_action
                item_stats = self.world.get_component(ai.current_target_id, ItemStats)
                yukkuri_stats = self.world.get_component(self.entity_id, YukkuriStats)

                if item_stats and yukkuri_stats:
                    if item_stats.nutrition > 0:
                        yukkuri_stats.hunger = max(0, yukkuri_stats.hunger - item_stats.nutrition)

                    if item_stats.fun > 0:
                        yukkuri_stats.happiness = min(100, yukkuri_stats.happiness + item_stats.fun)

                    if item_stats.comfort > 0:
                        yukkuri_stats.energy = min(100, yukkuri_stats.energy + item_stats.comfort)

                    if self.consume:
                        self.world.destroy_entity(ai.current_target_id)
                        if self.world.has_component(ai.current_target_id, Transform):
                            self.world.remove_component(ai.current_target_id, Transform)
                        ai.current_target_id = -1
                return Status.SUCCESS

        return Status.RUNNING

class Idle(Action):
    """
    Makes the entity idle (stop moving).
    """
    def __init__(self, name: str = "Idle", entity_id: Optional[int] = None, world: Optional['World'] = None, blackboard: Optional[Any] = None):
        """
        Initializes the Idle action.

        Args:
            name (str): The name of the behavior node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World instance.
            blackboard (Optional[Any]): The Behavior Tree blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        """
        Stops the entity's physics velocity.

        Returns:
            Status: Always returns SUCCESS.
        """
        if self.world is None or self.entity_id is None:
            return Status.SUCCESS # Or failure?

        phys = self.world.get_component(self.entity_id, PhysicsBody)
        if phys:
            phys.body.velocity = (0, 0)
        return Status.SUCCESS

class Check(Action):
    """
    A behavior node that checks a condition function.

    Attributes:
        check_fn (Callable[[], bool]): The function to check.
    """
    def __init__(self, name: str, check_fn: Callable[[], bool]):
            """
            Initializes the Check behavior.

            Args:
                name: The name of the behavior node.
                check_fn: The function to call. Should return True for success.
            """
            super().__init__(name)
            self.check_fn = check_fn

    def update(self) -> Status:
        """
        Evaluates the check function.

        Returns:
            Status: SUCCESS if check_fn returns True, else FAILURE.
        """
        if self.check_fn():
            return Status.SUCCESS
        return Status.FAILURE

# --- Behavior Tree Builder ---

class BehaviorRegistry:
    _goals: Dict[str, Callable[[int, 'World', int, int, Callable, Callable], Behaviour]] = {}

    @classmethod
    def register_goal(cls, goal_name: str, builder: Callable[[int, 'World', int, int, Callable, Callable], Behaviour]):
        cls._goals[goal_name] = builder

    @classmethod
    def get_goals(cls) -> Dict[str, Callable]:
        return cls._goals


def build_eat_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    eat_sequence = py_trees.composites.Sequence(name="Eat Sequence", memory=True)

    is_eating = Check(name="Goal=Eat?", check_fn=lambda: check_goal_fn("Eat"))

    eat_execution = py_trees.composites.Selector(name="Eat Execution", memory=True)

    # 2a. If we have a target, Go to it and Eat
    have_target_seq = py_trees.composites.Sequence(name="Have Target?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_fn)

    move_to_food = MoveToTarget(name="Move To Food", entity_id=entity_id, world=world)
    interact_food = Interact(name="Interact Food", entity_id=entity_id, world=world)

    have_target_seq.add_children([check_target, move_to_food, interact_food])

    # 2b. If no target, Find Food
    find_food = FindItem(name="Find Food", entity_id=entity_id, world=world, stat_criteria="nutrition")

    eat_execution.add_children([have_target_seq, find_food])
    eat_sequence.add_children([is_eating, eat_execution])
    return eat_sequence

class FindItem(Action):
    """
    Action to find an item based on criteria.
    """
    def __init__(self, name: str, entity_id: int, world: 'World', stat_criteria: str):
        super().__init__(name, entity_id, world)
        self.stat_criteria = stat_criteria

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
                return Status.FAILURE

        game_service = self.world.services.try_get(GameService)
        best_item = -1

        if game_service:
            best_item = game_service.find_best_item((trans.x, trans.y), self.stat_criteria)

        if best_item != -1:
            ai.current_target_id = best_item
            ai.path = None
            return Status.SUCCESS
        return Status.FAILURE

def build_sleep_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    sleep_sequence = py_trees.composites.Sequence(name="Sleep Sequence", memory=True)

    is_sleeping = Check(name="Goal=Sleep?", check_fn=lambda: check_goal_fn("Sleep"))

    sleep_execution = py_trees.composites.Selector(name="Sleep Execution", memory=True)

    # 1. If we have a target (bed), Go to it and Sleep
    have_target_seq = py_trees.composites.Sequence(name="Have Bed?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_fn)

    move_to_bed = MoveToTarget(name="Move To Bed", entity_id=entity_id, world=world)
    interact_bed = Interact(name="Sleep In Bed", entity_id=entity_id, world=world, consume=False)

    have_target_seq.add_children([check_target, move_to_bed, interact_bed])

    # 2. If no target, Find Bed
    find_bed = FindItem(name="Find Bed", entity_id=entity_id, world=world, stat_criteria="comfort")

    sleep_execution.add_children([have_target_seq, find_bed])
    sleep_sequence.add_children([is_sleeping, sleep_execution])
    return sleep_sequence

def build_play_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    play_sequence = py_trees.composites.Sequence(name="Play Sequence", memory=True)

    is_playing = Check(name="Goal=Play?", check_fn=lambda: check_goal_fn("Play"))

    play_execution = py_trees.composites.Selector(name="Play Execution", memory=True)

    # 1. If we have a target (toy), Go to it and Play
    have_target_seq = py_trees.composites.Sequence(name="Have Toy?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_fn)

    move_to_toy = MoveToTarget(name="Move To Toy", entity_id=entity_id, world=world)
    interact_toy = Interact(name="Play With Toy", entity_id=entity_id, world=world, consume=False)

    have_target_seq.add_children([check_target, move_to_toy, interact_toy])

    # 2. If no target, Find Toy
    find_toy = FindItem(name="Find Toy", entity_id=entity_id, world=world, stat_criteria="fun")

    play_execution.add_children([have_target_seq, find_toy])
    play_sequence.add_children([is_playing, play_execution])
    return play_sequence

def build_wander_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    wander_sequence = py_trees.composites.Sequence(name="Wander Sequence", memory=True)
    is_wandering = Check(name="Goal=Wander?", check_fn=lambda: check_goal_fn("Wander") or check_goal_fn("move_random"))
    wander = Wander(entity_id=entity_id, world=world, width=width, height=height)
    wander_sequence.add_children([is_wandering, wander])
    return wander_sequence

# Register default behaviors
BehaviorRegistry.register_goal("Eat", build_eat_behavior)
BehaviorRegistry.register_goal("Sleep", build_sleep_behavior)
BehaviorRegistry.register_goal("Play", build_play_behavior)
BehaviorRegistry.register_goal("Wander", build_wander_behavior)


def create_yukkuri_behavior_tree(entity_id: int, world: 'World', width: int, height: int) -> py_trees.composites.Sequence:
    """
    Builds the behavior tree for a Yukkuri.

    The tree structure uses a UtilitySelector to pick a goal, then executes that goal.

    Args:
        entity_id (int): The ID of the Yukkuri entity.
        world (World): The ECS World instance.
        width (int): The width of the world boundary.
        height (int): The height of the world boundary.

    Returns:
        py_trees.composites.Sequence: The root node of the behavior tree.
    """

    # Check Goal Condition
    def check_goal(goal_name: str) -> bool:
        ai = world.get_component(entity_id, AIState)
        if not ai:
            return False
        return bool(ai.current_action == goal_name)

    # Check Target Condition
    def check_target_exists() -> bool:
        ai = world.get_component(entity_id, AIState)
        if not ai or ai.current_target_id == -1:
            return False
        return world.has_component(ai.current_target_id, Transform)

    # --- Root Sequence ---
    # 1. Select Goal (UtilitySelector)
    # 2. Execute Goal (Selector)
    root = py_trees.composites.Sequence(name="Root Sequence", memory=False)

    # 1. Utility Selector
    utility_selector = UtilitySelector(entity_id=entity_id, world=world)
    root.add_child(utility_selector)

    # 2. Execution Selector
    execution_selector = py_trees.composites.Selector(name="Execution Selector", memory=False)

    goals = BehaviorRegistry.get_goals()

    # Add all registered goals to the execution selector
    # The order here matters less because each goal starts with a Check(Goal=X)
    # However, we should ensure we cover all potential goals returned by UtilitySelector

    for name, builder in goals.items():
        execution_selector.add_child(builder(entity_id, world, width, height, check_goal, check_target_exists))

    # Always add Idle at the end as a fallback
    idle = Idle(entity_id=entity_id, world=world)
    execution_selector.add_child(idle)

    root.add_child(execution_selector)

    return root
