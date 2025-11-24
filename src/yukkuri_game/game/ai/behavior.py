"""
Module defining the behavior tree logic for AI agents.
"""
import py_trees
import math
import random
import pymunk
from typing import Optional, Callable, Any, TYPE_CHECKING
from py_trees.behaviour import Behaviour
from py_trees.common import Status
from typing import Optional, Callable, Any, TYPE_CHECKING, Dict
from ..components import Transform, PhysicsBody, Velocity, InteractionRequest
from ..yukkuri_components import AIState, ItemStats, YukkuriStats
from .utility_selector import UtilitySelector
from .base_action import Action
from ..services import GameService
from .navigation_service import NavigationService
from .steering import Steering
from ...config import GameConfig

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
        self.last_position: Optional[Tuple[float, float]] = None
        self.stuck_timer: float = 0.0
        self.stuck_threshold: float = 1.0 # Seconds

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

        dt = py_trees.blackboard.Blackboard().get("dt")
        if dt is None:
             dt = 0.016
        dt = float(dt)

        # Stuck Detection
        if self.last_position:
            moved_dist = math.hypot(trans.x - self.last_position[0], trans.y - self.last_position[1])
            if moved_dist < (self.speed * dt * 0.1): # Moved less than 10% of expected speed
                 self.stuck_timer += dt
            else:
                 self.stuck_timer = 0.0

        self.last_position = (trans.x, trans.y)

        if self.stuck_timer > self.stuck_threshold:
             # If slightly stuck, try small random offset first
             # If really stuck, full repath
             self.stuck_timer = 0.0

             # Apply random force (wiggle)
             if phys:
                  angle = random.uniform(0, math.pi * 2)
                  force = 5000.0
                  phys.body.apply_impulse_at_local_point((math.cos(angle) * force, math.sin(angle) * force))

             # Also force repath
             ai.path = None
             return Status.RUNNING


        # Pathfinding
        if ai.path is None or len(ai.path) == 0:
             # Simple check to see if we need pathfinding or just straight line
             # For now, assuming pathfinding is always needed or available
             # Check if we are already at the target before calling pathfinding
             if math.hypot(target_pos[0] - trans.x, target_pos[1] - trans.y) < 15.0:
                 return Status.SUCCESS

             nav_service = self.world.services.try_get(NavigationService)
             if nav_service:
                 ai.path = nav_service.find_path((trans.x, trans.y), target_pos)
             else:
                 # Fallback if service not available (shouldn't happen)
                 return Status.FAILURE

             if not ai.path:
                 return Status.FAILURE

        # Move along path
        if len(ai.path) > 0:
            next_point = ai.path[0]

            # --- Raycast / Local Avoidance Check ---
            # Before trying to reach next_point, let's see if we can actually see it
            # or if we can see a further point (string pulling)

            if phys and phys.body and getattr(phys.body, 'space', None):
                # Check visibility to next waypoint
                query_start = (trans.x, trans.y)

                # String Pulling: Check if we can skip to further waypoints
                # Look ahead up to 3 nodes
                can_skip_to_index = -1
                for i in range(min(len(ai.path), 3) - 1, 0, -1):
                    target_node = ai.path[i]

                    # Raycast
                    shape_filter = pymunk.ShapeFilter(categories=0b1) # Assuming category 1 is for walls/obstacles
                    # Use segment_query to get all hits, then filter out self
                    hits = phys.body.space.segment_query(query_start, target_node, 1.0, shape_filter)

                    is_clear = True
                    for hit in hits:
                        # Check if hit.shape is valid (it should be)
                        if hit.shape is None:
                            continue

                        # Check if it's a sensor (sensors shouldn't block movement usually, but raycast hits them)
                        if hit.shape.sensor:
                            continue

                        if hit.shape.body != phys.body:
                            # Hit something that is not me

                            # Double check if the hit is really 0 distance (meaning we are overlapping it at start)
                            # segment_query returns hits along the segment.
                            # If alpha is 0, it's at the start point.
                            if hit.alpha < 0.001:
                                # We are inside an obstacle? Or just touching?
                                # If we are inside, we probably shouldn't consider it "blocking" the path forward if we are moving out of it?
                                # But for now, assume any hit is a block.
                                pass

                            is_clear = False
                            break

                    if is_clear:
                        # Clear path!
                        can_skip_to_index = i
                        break

                if can_skip_to_index > 0:
                    # We can skip intermediate nodes
                    for _ in range(can_skip_to_index):
                        ai.path.pop(0)
                    next_point = ai.path[0]

            # Re-calculate distance to (possibly new) next_point
            dx = next_point[0] - trans.x
            dy = next_point[1] - trans.y
            dist = math.hypot(dx, dy)

            # Check if we are close to the *final* target
            dist_to_final = math.hypot(target_pos[0] - trans.x, target_pos[1] - trans.y)
            # Use a threshold slightly smaller than the interaction range to ensure we are close enough to interact
            if dist_to_final < 15.0:
                ai.path = []
                return Status.SUCCESS

            if dist < 15.0: # Reached waypoint (increased threshold for smoother cornering)
                ai.path.pop(0)
                if not ai.path: # Reached end of path
                    return Status.SUCCESS
                # Recalculate next point
                next_point = ai.path[0]

            # Steering
            if phys:
                # Use Arrive for the last point, Seek for others
                if len(ai.path) == 1:
                    velocity = Steering.arrive((trans.x, trans.y), next_point, self.speed)
                else:
                    current_vel = (phys.body.velocity.x, phys.body.velocity.y)
                    velocity = Steering.seek((trans.x, trans.y), next_point, self.speed, current_vel)

                phys.body.velocity = velocity
                phys.body.activate()
            else:
                # Fallback to direct transform manipulation
                step = self.speed * dt
                if step > dist:
                    trans.x = next_point[0]
                    trans.y = next_point[1]
                else:
                    # Normalize
                    if dist > 0:
                         dx /= dist
                         dy /= dist
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

        Returns:
            None
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
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.add_component(self.entity_id, InteractionRequest(
                    target_id=ai.current_target_id,
                    consume=self.consume
                ))
            # We return SUCCESS immediately as the request is queued.
            # The system will handle the rest next frame.
            # If animations are needed, we might need to wait, but for now immediate success matches previous behavior.
            return Status.SUCCESS

        return Status.RUNNING

class SocialInteract(Action):
    """
    Handles social interaction with another Yukkuri.
    """
    def __init__(self, name: str, entity_id: int, world: 'World', interaction_type: str):
        """
        Initializes the SocialInteract action.

        Args:
            name (str): The name of the behavior node.
            entity_id (int): The ID of the entity.
            world (World): The ECS World instance.
            interaction_type (str): The type of interaction (e.g., "Talk", "Fight").
        """
        super().__init__(name, entity_id, world)
        self.interaction_type = interaction_type # "Talk", "Fight", "Dance"

    def update(self) -> Status:
        """
        Checks distance and performs the social interaction.

        Returns:
            Status: SUCCESS if interaction complete, RUNNING if waiting/moving closer, FAILURE if target invalid.
        """
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if not target_trans:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist <= 40.0: # Interaction range slightly larger for social
            game_service = self.world.services.try_get(GameService)
            if game_service:
                success = game_service.interact_social(self.entity_id, ai.current_target_id, self.interaction_type)
                return Status.SUCCESS if success else Status.FAILURE

        return Status.RUNNING

class FindSocialTarget(Action):
    """
    Finds a target Yukkuri for social interaction based on criteria.
    """
    def __init__(self, name: str, entity_id: int, world: 'World', criteria: str):
        """
        Initializes the FindSocialTarget action.

        Args:
            name (str): The name of the behavior node.
            entity_id (int): The ID of the entity.
            world (World): The ECS World instance.
            criteria (str): Criteria for selecting a target (e.g., "friend", "enemy", "any").
        """
        super().__init__(name, entity_id, world)
        self.criteria = criteria # "friend", "enemy", "any"

    def update(self) -> Status:
        """
        Searches for a suitable social target.

        Returns:
            Status: SUCCESS if target found, FAILURE otherwise.
        """
        super().update()
        if not self.world or not self.entity_id:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        my_stats = self.world.get_component(self.entity_id, YukkuriStats)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not my_stats or not trans:
            return Status.FAILURE

        nearby_yukkuris = self.world.get_entities_with(YukkuriStats, Transform)

        best_target = -1
        min_dist = float('inf')

        for uid in nearby_yukkuris:
            if uid == self.entity_id:
                continue

            u_stats = self.world.get_component(uid, YukkuriStats)
            u_trans = self.world.get_component(uid, Transform)

            # Check criteria
            is_compatible = (u_stats.type_id == my_stats.type_id)

            match = False
            if self.criteria == "any":
                match = True
            elif self.criteria == "friend" and is_compatible:
                match = True
            elif self.criteria == "enemy" and not is_compatible:
                match = True

            if match:
                dist = math.hypot(u_trans.x - trans.x, u_trans.y - trans.y)
                if dist < min_dist:
                    min_dist = dist
                    best_target = uid

        if best_target != -1:
            ai.current_target_id = best_target
            ai.path = None
            return Status.SUCCESS

        return Status.FAILURE

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
    """
    Registry for behavior tree construction functions associated with high-level goals.
    """
    _goals: Dict[str, Callable[[int, 'World', int, int, Callable, Callable], Behaviour]] = {}

    @classmethod
    def register_goal(cls, goal_name: str, builder: Callable[[int, 'World', int, int, Callable, Callable], Behaviour]):
        """
        Registers a behavior builder function for a specific goal.

        Args:
            goal_name (str): The name of the goal.
            builder (Callable): The function that builds the behavior subtree.
        """
        cls._goals[goal_name] = builder

    @classmethod
    def get_goals(cls) -> Dict[str, Callable]:
        """
        Retrieves all registered goals.

        Returns:
            Dict[str, Callable]: A dictionary mapping goal names to builder functions.
        """
        return cls._goals


def build_eat_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    """
    Builds the behavior subtree for the 'Eat' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
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

    Attributes:
        stat_criteria (str): The item stat to look for (e.g., "nutrition", "fun").
    """
    def __init__(self, name: str, entity_id: int, world: 'World', stat_criteria: str):
        """
        Initializes the FindItem action.

        Args:
            name (str): The name of the node.
            entity_id (int): The entity ID.
            world (World): The ECS World.
            stat_criteria (str): The stat criteria.
        """
        super().__init__(name, entity_id, world)
        self.stat_criteria = stat_criteria

    def update(self) -> Status:
        """
        Searches for the best item matching the criteria.

        Returns:
            Status: SUCCESS if item found, FAILURE otherwise.
        """
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
    """
    Builds the behavior subtree for the 'Sleep' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
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
    """
    Builds the behavior subtree for the 'Play' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
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
    """
    Builds the behavior subtree for the 'Wander' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
    wander_sequence = py_trees.composites.Sequence(name="Wander Sequence", memory=True)
    is_wandering = Check(name="Goal=Wander?", check_fn=lambda: check_goal_fn("Wander") or check_goal_fn("move_random"))
    wander = Wander(entity_id=entity_id, world=world, width=width, height=height)
    wander_sequence.add_children([is_wandering, wander])
    return wander_sequence

def build_talk_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    """
    Builds the behavior subtree for the 'Talk' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
    talk_sequence = py_trees.composites.Sequence(name="Talk Sequence", memory=True)
    is_talking = Check(name="Goal=Talk?", check_fn=lambda: check_goal_fn("Talk"))

    talk_execution = py_trees.composites.Selector(name="Talk Execution", memory=True)

    # 1. Have target?
    have_target_seq = py_trees.composites.Sequence(name="Have Friend?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_fn)
    move_to_friend = MoveToTarget(name="Move To Friend", entity_id=entity_id, world=world)
    do_talk = SocialInteract(name="Talk", entity_id=entity_id, world=world, interaction_type="Talk")
    have_target_seq.add_children([check_target, move_to_friend, do_talk])

    # 2. Find Friend
    find_friend = FindSocialTarget(name="Find Friend", entity_id=entity_id, world=world, criteria="friend")

    talk_execution.add_children([have_target_seq, find_friend])
    talk_sequence.add_children([is_talking, talk_execution])
    return talk_sequence

def build_fight_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    """
    Builds the behavior subtree for the 'Fight' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
    fight_sequence = py_trees.composites.Sequence(name="Fight Sequence", memory=True)
    is_fighting = Check(name="Goal=Fight?", check_fn=lambda: check_goal_fn("Fight"))

    fight_execution = py_trees.composites.Selector(name="Fight Execution", memory=True)

    # 1. Have target?
    have_target_seq = py_trees.composites.Sequence(name="Have Enemy?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_fn)
    move_to_enemy = MoveToTarget(name="Move To Enemy", entity_id=entity_id, world=world)
    do_fight = SocialInteract(name="Fight", entity_id=entity_id, world=world, interaction_type="Fight")
    have_target_seq.add_children([check_target, move_to_enemy, do_fight])

    # 2. Find Enemy
    find_enemy = FindSocialTarget(name="Find Enemy", entity_id=entity_id, world=world, criteria="enemy")

    fight_execution.add_children([have_target_seq, find_enemy])
    fight_sequence.add_children([is_fighting, fight_execution])
    return fight_sequence

def build_dance_behavior(entity_id: int, world: 'World', width: int, height: int, check_goal_fn: Callable, check_target_fn: Callable) -> Behaviour:
    """
    Builds the behavior subtree for the 'Dance' goal.

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Function to check if this is the current goal.
        check_target_fn (Callable): Function to check if the target exists.

    Returns:
        Behaviour: The behavior subtree.
    """
    dance_sequence = py_trees.composites.Sequence(name="Dance Sequence", memory=True)
    is_dancing = Check(name="Goal=Dance?", check_fn=lambda: check_goal_fn("Dance"))

    dance_execution = py_trees.composites.Selector(name="Dance Execution", memory=True)

    # 1. Have target? (Dance partner)
    have_target_seq = py_trees.composites.Sequence(name="Have Partner?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_fn)
    move_to_partner = MoveToTarget(name="Move To Partner", entity_id=entity_id, world=world)
    do_dance = SocialInteract(name="Dance", entity_id=entity_id, world=world, interaction_type="Dance")
    have_target_seq.add_children([check_target, move_to_partner, do_dance])

    # 2. Find Partner (Any)
    find_partner = FindSocialTarget(name="Find Partner", entity_id=entity_id, world=world, criteria="any")

    dance_execution.add_children([have_target_seq, find_partner])
    dance_sequence.add_children([is_dancing, dance_execution])
    return dance_sequence

# Register default behaviors
BehaviorRegistry.register_goal("Eat", build_eat_behavior)
BehaviorRegistry.register_goal("Sleep", build_sleep_behavior)
BehaviorRegistry.register_goal("Play", build_play_behavior)
BehaviorRegistry.register_goal("Wander", build_wander_behavior)
BehaviorRegistry.register_goal("Talk", build_talk_behavior)
BehaviorRegistry.register_goal("Fight", build_fight_behavior)
BehaviorRegistry.register_goal("Dance", build_dance_behavior)


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
        """
        Checks if the entity's current AI goal matches the given name.

        Args:
            goal_name (str): The goal to check.

        Returns:
            bool: True if matches, False otherwise.
        """
        ai = world.get_component(entity_id, AIState)
        if not ai:
            return False
        return bool(ai.current_action == goal_name)

    # Check Target Condition
    def check_target_exists() -> bool:
        """
        Checks if the entity's current target exists in the world.

        Returns:
            bool: True if target exists, False otherwise.
        """
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
