"""
Module defining the behavior tree logic for AI agents.
"""

import math
import random
import time
from typing import TYPE_CHECKING, Any, Optional, cast
from collections.abc import Callable

import py_trees
import pymunk
from py_trees.behaviour import Behaviour
from py_trees.common import Status

from ..components import (
    InteractionRequest,
    MovementController,
    PhysicsBody,
    Transform,
    LightSource,
)
from ..services import GameService
from ..yukkuri_components import (
    AIState,
    ItemStats,
    YukkuriStats,
    Needs,
    EmotionalState,
    Predator,
    Flight,
    FlightState,
)
from .base_action import Action
from .navigation_service import NavigationService
from .navigation_constants import TraversalCapability
from .utility_selector import UtilitySelector

from ...engine.types import EntityID

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World


# --- Behavior Tree Leaves (Actions) ---


class MoveToTarget(Action):
    """
    Moves the entity towards a target using direct velocity control.

    Attributes:
        speed (float): The movement speed.
        acceptance_radius (float): The distance at which the target is considered reached.
    """

    def __init__(
        self,
        name: str = "Move To Target",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
        speed: float = 100.0,
        acceptance_radius: float = 15.0,
    ):
        """
        Initializes the MoveToTarget action.

        Args:
            name (str): The name of the behavior node.
            entity_id (Optional[int]): The ID of the entity.
            world (Optional[World]): The ECS World instance.
            blackboard (Optional[Any]): The Behavior Tree blackboard.
            speed (float): Movement speed in pixels per second.
            acceptance_radius (float): Distance threshold for reaching target.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.speed = speed
        self.acceptance_radius = acceptance_radius

    def update(self) -> Status:
        """
        Calculates the velocity required to move towards the target and sets it
        in the MovementController.

        Returns:
            Status: RUNNING while moving, SUCCESS when reached, FAILURE if target invalid or lost.
        """
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)
        needs = self.world.get_component(self.entity_id, Needs)
        controller = self.world.get_component(self.entity_id, MovementController)

        if ai is None or trans is None or needs is None or controller is None:
            return Status.FAILURE

        # Determine Target Position (Entity or Coordinate)
        target_pos = None
        if ai.current_target_id != -1:
            target_trans = self.world.get_component(ai.current_target_id, Transform)
            if target_trans:
                target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
            else:
                ai.current_target_id = cast(EntityID, -1)
                controller.target_velocity = pymunk.Vec2d(0, 0)
                return Status.FAILURE
        elif (
            ai.state_data
            and "target_x" in ai.state_data
            and "target_y" in ai.state_data
        ):
            target_pos = pymunk.Vec2d(
                ai.state_data["target_x"], ai.state_data["target_y"]
            )

        if target_pos is None:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            return Status.FAILURE

        current_pos = pymunk.Vec2d(trans.x, trans.y)

        # Close-Range / Line-of-Sight Optimization (Direct Pursuit)
        # Bypasses pathfinding if target is visible and either:
        # 1. Within 150px (close-range), OR
        # 2. Within 400px AND there's clear line-of-sight (no obstacles)
        is_visible = ai.current_target_id == -1 or (ai.current_target_id in ai.visible_entities)
        
        if is_visible and target_pos:
            dist_to_target = (target_pos - current_pos).length
            
            use_direct_steering = False
            
            if dist_to_target < 150.0:
                # Close-range: always use direct steering
                use_direct_steering = True
            elif dist_to_target < 400.0:
                # Medium range: check line-of-sight
                from ..systems.physics import PhysicsSystem
                physics_sys = self.world.services.try_get(PhysicsSystem)
                if physics_sys and hasattr(physics_sys, 'space'):
                    space = physics_sys.space
                    # Raycast from current to target
                    filter_ = pymunk.ShapeFilter(mask=pymunk.ShapeFilter.ALL_MASKS())
                    hit = space.segment_query_first(current_pos, target_pos, 1.0, filter_)
                    
                    # Clear LOS if no hit, or hit is the target itself
                    if hit is None:
                        use_direct_steering = True
                    elif hit.shape:
                        # Check if hit shape belongs to target entity
                        target_phys = self.world.try_get_component(ai.current_target_id, PhysicsBody)
                        if target_phys and hit.shape.body == target_phys.body:
                            use_direct_steering = True
            
            if use_direct_steering:
                # Check if we are close enough to finish
                if dist_to_target < self.acceptance_radius:
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    ai.path = None
                    return Status.SUCCESS
                 
                # Direct Steering
                speed_modifier = 1.0
                if needs.energy < 30:
                    speed_modifier = 0.5
                 
                final_speed = self.speed * speed_modifier
                controller.target_velocity = (target_pos - current_pos).normalized() * final_speed
                 
                # Ensure path is cleared so we don't fall back to old path if we move out of range
                if ai.path:
                    ai.path = None
                 
                return Status.RUNNING

        # Pathfinding (Async)
        # If path is not set, try to find one.
        if ai.path is None:
            # Check if we are already requesting/handling state
            state_data = ai.state_data if ai.state_data else {}
            is_requesting = state_data.get("path_requesting", False)
            path_failed = state_data.get("path_failed", False)

            if is_requesting:
                # Check for failure or timeout
                now = time.time()
                request_timestamp = state_data.get("path_request_time", 0.0)
                
                # Timeout Control (0.5s)
                if (now - request_timestamp) > 0.5:
                     # Timed out waiting for path. Fallback to direct movement.
                     state_data["path_requesting"] = False
                     # We don't delete "path_failed" here, we just treat it as if we have no path yet.
                     # Fall through to Fallback logic below (ai.path is None)
                     pass
                elif path_failed:
                    state_data["path_requesting"] = False
                    if "path_failed" in state_data:
                        del state_data["path_failed"]
                    ai.state_data = state_data
                    # Proceed to Fallback below
                else:
                    return Status.RUNNING  # Waiting for path
            elif not path_failed:  # If we haven't just failed, request a path
                nav_service = self.world.services.try_get(NavigationService)
                if nav_service:
                    # Check for flight capability
                    capabilities = TraversalCapability.WALK
                    flight_comp = self.world.try_get_component(self.entity_id, Flight)
                    if flight_comp and flight_comp.stamina > 20:
                        capabilities |= TraversalCapability.FLY
                        # Trigger takeoff if needed for air pathing
                        if flight_comp.state == FlightState.GROUNDED:
                            flight_comp.state = FlightState.TAKEOFF
                    
                    # Determining Priority
                    priority = 2 # Normal
                    if ai.state_data and ai.state_data.get("pursuit_repath", False):
                        priority = 0 # High Priority for pursuit catch-up
                        ai.state_data["pursuit_repath"] = False # Consume flag

                    nav_service.request_path(
                        self.entity_id,
                        (trans.x, trans.y),
                        (target_pos.x, target_pos.y),
                        capabilities=capabilities,
                        priority=priority
                    )

                    if ai.state_data is None:
                        ai.state_data = {}
                    ai.state_data["path_requesting"] = True
                    ai.state_data["path_request_time"] = time.time() # Stamp for timeout
                    # Store destination to check for drift
                    ai.state_data["path_destination"] = (target_pos.x, target_pos.y)
                    # Clear failure flag if present
                    if "path_failed" in ai.state_data:
                        del ai.state_data["path_failed"]

                    return Status.RUNNING

        # Dynamic Path Invalidation (Drift Detection)
        # Check if target has moved significantly from the path's destination
        if ai.path and target_pos:
            is_visible = ai.current_target_id == -1 or (ai.current_target_id in ai.visible_entities)
            
            # Update Last Known Position if visible
            if is_visible:
                 if ai.state_data is None: ai.state_data = {}
                 ai.state_data["last_known_x"] = target_pos.x
                 ai.state_data["last_known_y"] = target_pos.y

                 # Check Drift with Adaptive Threshold
                 path_dest = ai.state_data.get("path_destination")
                 if path_dest:
                     # Calculate Adaptive Threshold
                     drift_threshold_sq = 2500.0 # Default 50px
                     
                     target_phys = self.world.try_get_component(ai.current_target_id, PhysicsBody)
                     if target_phys and target_phys.body:
                         # Faster target = Tighter threshold (repath sooner)
                         # Simple curve: Speed 0 -> 50px. Speed 100 -> 30px.
                         t_speed = target_phys.body.velocity.length
                         # threshold = max(30, 50 - t_speed * 0.2)?
                         # Let's map 0..100 to 50..20
                         val = max(20.0, 50.0 - (t_speed * 0.3))
                         drift_threshold_sq = val * val
                     
                     drift_sq = (target_pos - pymunk.Vec2d(*path_dest)).length_squared
                     if drift_sq > drift_threshold_sq:
                         now = time.time()
                         last_repath_time = ai.state_data.get("last_repath_time", 0.0)
                         # Cooldown can also be adaptive? 
                         # Keep 0.5s for now to avoid spam.
                         if now - last_repath_time > 0.5:
                             ai.path = None
                             ai.state_data["last_repath_time"] = now
                             ai.state_data["pursuit_repath"] = True
                             return Status.RUNNING

        # Fallback to Direct Movement if no path (Navigation missing or pathfinding failed/unnecessary)
        # Also handles clearing "path_requesting" flag if we fallback
        if ai.path is None:
            if ai.state_data and ai.state_data.get("path_requesting"):
                ai.state_data["path_requesting"] = False

            # Calculate vector to target directly
            vector_to_target = target_pos - pymunk.Vec2d(trans.x, trans.y)
            dist = vector_to_target.length

            if dist < self.acceptance_radius:
                controller.target_velocity = pymunk.Vec2d(0, 0)
                return Status.SUCCESS

            # Simple speed modifier
            speed_modifier = 1.0
            if needs.energy < 30:
                speed_modifier = 0.5

            final_speed = self.speed * speed_modifier
            if dist > 0.001:
                controller.target_velocity = vector_to_target.normalized() * final_speed
            else:
                controller.target_velocity = pymunk.Vec2d(0, 0)

            return Status.RUNNING

        # Path Follower Logic (Delegated to SteeringSystem)
        current_pos = pymunk.Vec2d(trans.x, trans.y)
        dist_to_final = (target_pos - current_pos).length

        if dist_to_final < self.acceptance_radius:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            ai.path = []
            return Status.SUCCESS

        return Status.RUNNING


class Wander(Action):
    """
    Causes the entity to wander to a random location.

    Attributes:
        width (int): The width of the area to wander within.
        height (int): The height of the area to wander within.
        move_action (Optional[MoveToTarget]): The underlying move action used to reach the random target.
    """

    def __init__(
        self,
        name: str = "Wander",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
        width: int = 3000,
        height: int = 3000,
    ):
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
        self.move_action: MoveToTarget | None = None

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
            ai.path = None  # Reset path

        # Create a temporary MoveToTarget to handle the actual movement logic
        self.move_action = MoveToTarget(
            entity_id=self.entity_id, world=self.world, blackboard=self.blackboard
        )

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

    Attributes:
        consume (bool): Whether the interaction should consume the target.
    """

    def __init__(
        self,
        name: str = "Interact",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
        consume: bool = True,
    ):
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

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            # If target lost or not set, check if we can find it again locally or fail
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if target_trans is None:
            # print("Interact Fail: Target trans missing")
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        # print(f"Interact Check: Dist={dist}")
        if dist <= 30.0:  # Interaction range
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id, consume=self.consume
                    ),
                )
            # We return SUCCESS immediately as the request is queued.
            # The system will handle the rest next frame.
            return Status.SUCCESS

        return Status.RUNNING


class SocialInteract(Action):
    """
    Handles social interaction with another Yukkuri.

    Attributes:
        interaction_type (str): The type of interaction (e.g., "Talk", "Fight", "Dance").
    """

    def __init__(
        self, name: str, entity_id: int, world: "World", interaction_type: str
    ):
        """
        Initializes the SocialInteract action.

        Args:
            name (str): The name of the behavior node.
            entity_id (int): The ID of the entity.
            world (World): The ECS World instance.
            interaction_type (str): The type of interaction (e.g., "Talk", "Fight").
        """
        super().__init__(name, entity_id, world)
        self.interaction_type = interaction_type  # "Talk", "Fight", "Dance"

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

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if target_trans is None:
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist <= 40.0:  # Interaction range slightly larger for social
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id,
                        consume=False,
                        action=self.interaction_type,
                    ),
                )
                return Status.SUCCESS

        return Status.RUNNING


class FindSocialTarget(Action):
    """
    Finds a target Yukkuri for social interaction based on criteria.

    Attributes:
        criteria (str): Criteria for selecting a target (e.g., "friend", "enemy", "any").
    """

    def __init__(self, name: str, entity_id: int, world: "World", criteria: str):
        """
        Initializes the FindSocialTarget action.

        Args:
            name (str): The name of the behavior node.
            entity_id (int): The ID of the entity.
            world (World): The ECS World instance.
            criteria (str): Criteria for selecting a target (e.g., "friend", "enemy", "any").
        """
        super().__init__(name, entity_id, world)
        self.criteria = criteria  # "friend", "enemy", "any"

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

        if ai is None or my_stats is None or trans is None:
            return Status.FAILURE

        nearby_yukkuris = self.world.get_entities_with(YukkuriStats, Transform)

        best_target = -1
        min_dist = float("inf")

        for uid in nearby_yukkuris:
            if uid == self.entity_id:
                continue

            # Skip failed targets
            if uid in ai.failed_targets:
                continue

            u_stats = self.world.get_component(uid, YukkuriStats)
            u_trans = self.world.get_component(uid, Transform)

            if u_stats is None or u_trans is None:
                continue

            # Check criteria
            is_compatible = u_stats.type_id == my_stats.type_id

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
            if ai.current_target_id != best_target:
                ai.current_target_id = cast(EntityID, best_target)
                ai.path = None
            return Status.SUCCESS

        return Status.FAILURE


class Idle(Action):
    """
    Makes the entity idle (stop moving).
    """

    def __init__(
        self,
        name: str = "Idle",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
    ):
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
            return Status.SUCCESS  # Or failure?

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


class CheckEmotion(Action):
    """
    Checks the emotional state of the entity.

    Attributes:
        check_fn (Callable[[EmotionalState], bool]): The function to evaluate the emotion.
    """

    def __init__(
        self,
        name: str,
        entity_id: int,
        world: "World",
        check_fn: Callable[[EmotionalState], bool],
    ):
        """
        Initializes the CheckEmotion action.

        Args:
            name (str): The name of the node.
            entity_id (int): The entity ID.
            world (World): The ECS World.
            check_fn (Callable[[EmotionalState], bool]): Predicate function.
        """
        super().__init__(name, entity_id, world)
        self.check_fn = check_fn

    def update(self) -> Status:
        """
        Evaluates the emotional state check.

        Returns:
            Status: SUCCESS if check_fn returns True, else FAILURE.
        """
        if not self.world or not self.entity_id:
            return Status.FAILURE
        emotion = self.world.get_component(self.entity_id, EmotionalState)
        if emotion and self.check_fn(emotion):
            return Status.SUCCESS
        return Status.FAILURE


# --- Behavior Tree Builder ---


class BehaviorRegistry:
    """
    Registry for behavior tree construction functions associated with high-level goals.
    """

    _goals: dict[
        str,
        Callable[
            [int, "World", int, int, Callable[[str], bool], Callable[[], bool]],
            Behaviour,
        ],
    ] = {}
    _target_requirements: dict[str, type[Any]] = {}

    @classmethod
    def register_goal(
        cls,
        goal_name: str,
        builder: Callable[
            [int, "World", int, int, Callable[[str], bool], Callable[[], bool]],
            Behaviour,
        ],
        required_component: type[Any] | None = None,
    ) -> None:
        """
        Registers a behavior builder function for a specific goal.

        Args:
            goal_name (str): The name of the goal.
            builder (Callable): The function that builds the behavior subtree.
            required_component (Optional[Type[Any]]): The component required on the target.
        """
        cls._goals[goal_name] = builder
        if required_component:
            cls._target_requirements[goal_name] = required_component

    @classmethod
    def get_goals(
        cls,
    ) -> dict[
        str,
        Callable[
            [int, "World", int, int, Callable[[str], bool], Callable[[], bool]],
            Behaviour,
        ],
    ]:
        """
        Retrieves all registered goals.

        Returns:
            Dict[str, Callable]: A dictionary mapping goal names to builder functions.
        """
        return cls._goals

    @classmethod
    def get_target_requirement(cls, goal_name: str) -> type[Any] | None:
        """
        Retrieves the required component type for a goal's target.

        Args:
            goal_name (str): The name of the goal.

        Returns:
            Optional[Type[Any]]: The required component type or None.
        """
        return cls._target_requirements.get(goal_name)


def build_eat_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    # Use memory=False to ensure we re-evaluate children (allowing for target switching)
    eat_sequence = py_trees.composites.Sequence(name="Eat Sequence", memory=False)

    is_eating = Check(name="Goal=Eat?", check_fn=lambda: check_goal_fn("Eat"))

    # Execution Sequence:
    # 1. Ensure we have the BEST target (FindItem).
    # 2. Move to target.
    # 3. Interact.
    eat_execution = py_trees.composites.Sequence(name="Eat Execution", memory=False)

    # FindFood will find the best food. If it changes target, it updates AIState and clears path.
    # If no food is found, it fails, aborting the sequence.
    find_food = FindItem(
        name="Find Best Food",
        entity_id=entity_id,
        world=world,
        stat_criteria="nutrition",
    )

    move_to_food = MoveToTarget(
        name="Move To Food", entity_id=entity_id, world=world, acceptance_radius=30.0
    )
    interact_food = Interact(name="Interact Food", entity_id=entity_id, world=world)

    eat_execution.add_children([find_food, move_to_food, interact_food])
    eat_sequence.add_children([is_eating, eat_execution])
    return eat_sequence


class FindItem(Action):
    """
    Action to find an item based on criteria.

    Attributes:
        stat_criteria (str): The item stat to look for (e.g., "nutrition", "fun").
    """

    def __init__(self, name: str, entity_id: int, world: "World", stat_criteria: str):
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

        if ai is None or trans is None:
            return Status.FAILURE

        game_service = self.world.services.try_get(GameService)
        best_item = -1

        if game_service:
            best_item = game_service.find_best_item(
                (trans.x, trans.y),
                self.stat_criteria,
                exclude_ids={int(x) for x in ai.failed_targets},
                searcher_id=self.entity_id,
            )

        if best_item != -1:
            # Only update and clear path if the target actually changed
            if ai.current_target_id != best_item:
                ai.current_target_id = cast(EntityID, best_item)
                ai.path = None  # Force re-pathing

                # Anticipatory Caching: Request path immediately with LOW priority
                nav_service = self.world.services.try_get(NavigationService)
                target_trans = self.world.get_component(best_item, Transform)
                if nav_service and target_trans:
                    # Check capabilities (Duplicate logic from MoveToTarget, could be helper)
                    capabilities = TraversalCapability.WALK
                    flight_comp = self.world.try_get_component(self.entity_id, Flight)
                    if flight_comp and flight_comp.stamina > 20:
                        capabilities |= TraversalCapability.FLY

                    nav_service.request_path(
                        self.entity_id,
                        (trans.x, trans.y),
                        (target_trans.x, target_trans.y),
                        capabilities=capabilities,
                        priority=0,  # LOW priority
                    )
                    # Mark as requesting so MoveToTarget doesn't double request immediately
                    if ai.state_data is None:
                        ai.state_data = {}
                    ai.state_data["path_requesting"] = True
                    if "path_failed" in ai.state_data:
                        del ai.state_data["path_failed"]

            return Status.SUCCESS

        # If no item found, but we have ignored some targets (failed previously),
        # clear the failed list so we can retry them next frame.
        if ai.failed_targets:
            ai.failed_targets.clear()

        return Status.FAILURE


class FindLightSource(Action):
    """
    Action to find the nearest light source.
    """

    def __init__(self, name: str, entity_id: int, world: "World"):
        super().__init__(name, entity_id, world)

    def update(self) -> Status:
        super().update()
        if not self.world or not self.entity_id:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
            return Status.FAILURE

        # Find nearest LightSource
        # We can iterate all entities with LightSource.
        # Ideally should use SectorMap or SpatialHash, but iteration is fine for now if lights are few.
        best_dist = float("inf")
        best_light = -1

        for ent, (l_trans, light) in self.world.get_components_tuple(
            Transform, LightSource
        ):
            if ent == self.entity_id:
                continue

            # Use light.radius to check if it's even relevant? Or just center?
            # We want to be *inside* the light usually, or near it.
            # Let's find the center of the light.

            dist = math.hypot(l_trans.x - trans.x, l_trans.y - trans.y)
            if dist < best_dist:
                best_dist = dist
                best_light = ent

        if best_light != -1:
            if ai.current_target_id != best_light:
                ai.current_target_id = cast(EntityID, best_light)
                ai.path = None
            return Status.SUCCESS

        return Status.FAILURE


def build_sleep_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    sleep_sequence = py_trees.composites.Sequence(name="Sleep Sequence", memory=False)

    is_sleeping = Check(name="Goal=Sleep?", check_fn=lambda: check_goal_fn("Sleep"))
    sleep_execution = py_trees.composites.Sequence(name="Sleep Execution", memory=False)

    # 1. Find best bed
    find_bed = FindItem(
        name="Find Best Bed", entity_id=entity_id, world=world, stat_criteria="comfort"
    )

    move_to_bed = MoveToTarget(
        name="Move To Bed", entity_id=entity_id, world=world, acceptance_radius=30.0
    )
    interact_bed = Interact(
        name="Sleep In Bed", entity_id=entity_id, world=world, consume=False
    )

    sleep_execution.add_children([find_bed, move_to_bed, interact_bed])
    sleep_sequence.add_children([is_sleeping, sleep_execution])
    return sleep_sequence


def build_play_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    play_sequence = py_trees.composites.Sequence(name="Play Sequence", memory=False)

    is_playing = Check(name="Goal=Play?", check_fn=lambda: check_goal_fn("Play"))
    play_execution = py_trees.composites.Sequence(name="Play Execution", memory=False)

    # 1. Find best toy
    find_toy = FindItem(
        name="Find Best Toy", entity_id=entity_id, world=world, stat_criteria="fun"
    )

    move_to_toy = MoveToTarget(
        name="Move To Toy", entity_id=entity_id, world=world, acceptance_radius=30.0
    )
    interact_toy = Interact(
        name="Play With Toy", entity_id=entity_id, world=world, consume=False
    )

    play_execution.add_children([find_toy, move_to_toy, interact_toy])
    play_sequence.add_children([is_playing, play_execution])
    return play_sequence


def build_wander_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    is_wandering = Check(
        name="Goal=Wander?",
        check_fn=lambda: check_goal_fn("Wander") or check_goal_fn("move_random"),
    )
    wander = Wander(entity_id=entity_id, world=world, width=width, height=height)
    wander_sequence.add_children([is_wandering, wander])
    return wander_sequence


def build_talk_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    talk_sequence = py_trees.composites.Sequence(name="Talk Sequence", memory=False)
    is_talking = Check(name="Goal=Talk?", check_fn=lambda: check_goal_fn("Talk"))

    talk_execution = py_trees.composites.Sequence(name="Talk Execution", memory=False)

    find_friend = FindSocialTarget(
        name="Find Best Friend", entity_id=entity_id, world=world, criteria="friend"
    )

    move_to_friend = MoveToTarget(
        name="Move To Friend",
        entity_id=entity_id,
        world=world,
        acceptance_radius=40.0,
    )
    do_talk = SocialInteract(
        name="Talk", entity_id=entity_id, world=world, interaction_type="Talk"
    )

    talk_execution.add_children([find_friend, move_to_friend, do_talk])
    talk_sequence.add_children([is_talking, talk_execution])
    return talk_sequence


def build_fight_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    fight_sequence = py_trees.composites.Sequence(name="Fight Sequence", memory=False)
    is_fighting = Check(name="Goal=Fight?", check_fn=lambda: check_goal_fn("Fight"))

    fight_execution = py_trees.composites.Sequence(name="Fight Execution", memory=False)

    find_enemy = FindSocialTarget(
        name="Find Best Enemy", entity_id=entity_id, world=world, criteria="enemy"
    )

    move_to_enemy = MoveToTarget(
        name="Move To Enemy",
        entity_id=entity_id,
        world=world,
        acceptance_radius=40.0,
    )
    do_fight = SocialInteract(
        name="Fight", entity_id=entity_id, world=world, interaction_type="Fight"
    )

    fight_execution.add_children([find_enemy, move_to_enemy, do_fight])
    fight_sequence.add_children([is_fighting, fight_execution])
    return fight_sequence


def build_dance_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    dance_sequence = py_trees.composites.Sequence(name="Dance Sequence", memory=False)
    is_dancing = Check(name="Goal=Dance?", check_fn=lambda: check_goal_fn("Dance"))

    dance_execution = py_trees.composites.Sequence(name="Dance Execution", memory=False)

    find_partner = FindSocialTarget(
        name="Find Best Partner", entity_id=entity_id, world=world, criteria="any"
    )

    move_to_partner = MoveToTarget(
        name="Move To Partner",
        entity_id=entity_id,
        world=world,
        acceptance_radius=40.0,
    )
    do_dance = SocialInteract(
        name="Dance", entity_id=entity_id, world=world, interaction_type="Dance"
    )

    dance_execution.add_children([find_partner, move_to_partner, do_dance])
    dance_sequence.add_children([is_dancing, dance_execution])
    return dance_sequence


def build_seek_light_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
    """
    Builds the behavior subtree for seeking light (at night or when stressed).
    """
    seek_sequence = py_trees.composites.Sequence(
        name="Seek Light Sequence", memory=False
    )
    is_seeking = Check(
        name="Goal=SeekLight?", check_fn=lambda: check_goal_fn("SeekLight")
    )

    seek_execution = py_trees.composites.Sequence(
        name="Seek Light Execution", memory=False
    )

    find_light = FindLightSource(name="Find Light", entity_id=entity_id, world=world)
    # Move close (e.g. 50 units)
    move_to_light = MoveToTarget(
        name="Move To Light", entity_id=entity_id, world=world, acceptance_radius=50.0
    )
    # Idle there? Or loop? MoveToTarget success means we are there.
    # We can just idle if we are there.

    seek_execution.add_children([find_light, move_to_light])
    seek_sequence.add_children([is_seeking, seek_execution])
    return seek_sequence


# Register default behaviors
BehaviorRegistry.register_goal("Eat", build_eat_behavior, required_component=ItemStats)
BehaviorRegistry.register_goal(
    "Sleep", build_sleep_behavior, required_component=ItemStats
)
BehaviorRegistry.register_goal(
    "SeekLight", build_seek_light_behavior, required_component=LightSource
)
BehaviorRegistry.register_goal(
    "Play", build_play_behavior, required_component=ItemStats
)
BehaviorRegistry.register_goal("Wander", build_wander_behavior)
BehaviorRegistry.register_goal(
    "Talk", build_talk_behavior, required_component=YukkuriStats
)
BehaviorRegistry.register_goal(
    "Fight", build_fight_behavior, required_component=YukkuriStats
)
BehaviorRegistry.register_goal(
    "Dance", build_dance_behavior, required_component=YukkuriStats
)


def create_yukkuri_behavior_tree(
    entity_id: int, world: "World", width: int, height: int
) -> py_trees.composites.Selector:
    """
    Builds the behavior tree for a Yukkuri.

    The tree structure is a high-level Selector with two branches:
    1. Stress Break (Emergency)
    2. Normal Behavior (Utility Selection + Execution)

    Args:
        entity_id (int): The ID of the Yukkuri entity.
        world (World): The ECS World instance.
        width (int): The width of the world boundary.
        height (int): The height of the world boundary.

    Returns:
        py_trees.composites.Selector: The root node of the behavior tree.
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

        has_trans = world.has_component(ai.current_target_id, Transform)
        if not has_trans:
            return False

        # Context-aware check using BehaviorRegistry metadata
        req_comp = BehaviorRegistry.get_target_requirement(ai.current_action)
        if req_comp:
            return world.has_component(ai.current_target_id, req_comp)

        return True

    # --- Root Structure ---
    # We use a Selector (Fall-back) node at the root.
    # It tries the first child (Stress Break). If that fails (not stressed),
    # it proceeds to the Normal Behavior.

    root_selector = py_trees.composites.Selector(name="Root Selector", memory=False)

    # Branch 1: Stress Break
    # If Stress > 90, we interrupt normal behavior.
    stress_break = py_trees.composites.Sequence(name="Stress Break", memory=False)
    check_stress = CheckEmotion(
        name="High Stress?",
        entity_id=entity_id,
        world=world,
        check_fn=lambda e: e.stress > 90,
    )
    # For now, panic is just Idle (freeze in terror) or maybe random movement later.
    # We can reuse Idle for "Freeze".
    panic_action = Idle(name="Panic Freeze", entity_id=entity_id, world=world)
    stress_break.add_children([check_stress, panic_action])

    root_selector.add_child(stress_break)

    # Branch 2: Self Preservation (Flee from Predators)
    flee_sequence = py_trees.composites.Sequence(name="Self Preservation", memory=False)
    # Check if any predator is nearby (simplified for behavior tree structure)
    # Ideally we use a sensor, but here we can just try the action which fails if no predator.
    flee_action = FleePredator(name="Flee Predator", entity_id=entity_id, world=world)
    flee_sequence.add_child(flee_action)

    # Only flee if running
    # We wrap it in a condition or just let it fail?
    # FleePredator returns SUCCESS if safe, RUNNING if fleeing, FAILURE if error.
    # If safe (SUCCESS), we don't want to stop checking other behaviors?
    # Actually if Flee returns SUCCESS (Safe), we want to proceed to Normal Behavior.
    # But Selector picks the first SUCCESS/RUNNING.
    # So Flee should return FAILURE if safe, RUNNING if fleeing.
    # Let's adjust FleePredator to return FAILURE if "No Threat".

    root_selector.add_child(flee_sequence)

    # Branch 3: Normal Behavior
    # Sequence: 1. Select Best Utility -> 2. Execute that Utility
    normal_behavior = py_trees.composites.Sequence(name="Normal Behavior", memory=False)

    # 1. Utility Selector
    # Evaluates all available actions and sets the highest scoring one in AIState.
    utility_selector = UtilitySelector(entity_id=entity_id, world=world)
    normal_behavior.add_child(utility_selector)

    # 2. Execution Selector
    # Tries to run the behavior tree corresponding to the selected action.
    execution_selector = py_trees.composites.Selector(
        name="Execution Selector", memory=False
    )

    goals = BehaviorRegistry.get_goals()

    for name, builder in goals.items():
        execution_selector.add_child(
            builder(entity_id, world, width, height, check_goal, check_target_exists)
        )

    # Fallback to Idle if no specific action succeeds
    idle = Idle(entity_id=entity_id, world=world)
    execution_selector.add_child(idle)

    normal_behavior.add_child(execution_selector)
    root_selector.add_child(normal_behavior)

    return root_selector


# --- Predator Hunting Behaviors ---


class FindPrey(Action):
    """
    Action to find prey entities based on the Predator component's prey_tags.
    """

    def __init__(
        self,
        name: str = "Find Prey",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
    ):
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        """
        Searches for valid prey entities within sensor range.
        """
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        predator = self.world.get_component(self.entity_id, Predator)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or predator is None or trans is None:
            return Status.FAILURE

        if not predator.prey_tags:
            return Status.FAILURE

        # Search for prey
        best_target = -1
        min_dist = float("inf")

        # Get all Yukkuris
        for uid, (u_stats, u_trans) in self.world.get_components_tuple(
            YukkuriStats, Transform
        ):
            if uid == self.entity_id:
                continue
            if uid in ai.failed_targets:
                continue

            # Check if this entity has any of the prey tags
            # For now, we check type_id against prey_tags
            if u_stats.type_id not in predator.prey_tags:
                # Also check for special tags like "Prey" or "Weak"
                # This would require a Tags component, for now we skip
                continue

            dist = math.hypot(u_trans.x - trans.x, u_trans.y - trans.y)
            if dist <= predator.prey_sense_radius and dist < min_dist:
                min_dist = dist
                best_target = uid

        if best_target != -1:
            if ai.current_target_id != best_target:
                ai.current_target_id = cast(EntityID, best_target)
                ai.path = None
            return Status.SUCCESS

        return Status.FAILURE


class EatPrey(Action):
    """
    Channeling action that locks both predator and prey, dealing damage over time.
    """

    def __init__(
        self,
        name: str = "Eat Prey",
        entity_id: int | None = None,
        world: Optional["World"] = None,
        blackboard: Any | None = None,
    ):
        super().__init__(name, entity_id, world, blackboard)
        self._eating_progress: float = 0.0

    def initialise(self) -> None:
        """Reset eating progress when starting."""
        self._eating_progress = 0.0

    def update(self) -> Status:
        """
        Deals damage to prey over time. Returns SUCCESS when prey is consumed.
        """
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        predator = self.world.get_component(self.entity_id, Predator)
        trans = self.world.get_component(self.entity_id, Transform)
        controller = self.world.get_component(self.entity_id, MovementController)

        if ai is None or predator is None or trans is None:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        # Check target still exists and has Needs
        target_trans = self.world.try_get_component(ai.current_target_id, Transform)
        target_needs = self.world.try_get_component(ai.current_target_id, Needs)
        target_controller = self.world.try_get_component(
            ai.current_target_id, MovementController
        )

        if target_trans is None or target_needs is None:
            return Status.FAILURE

        # Check distance
        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist > 40.0:
            return Status.RUNNING  # Need to get closer

        # --- Social Defense (Rescue) Check ---
        # If a non-predator Yukkuri is within rescue range, abort the eating
        rescue_radius = 60.0
        for defender_id, (d_stats, d_trans) in self.world.get_components_tuple(
            YukkuriStats, Transform
        ):
            if defender_id == self.entity_id:
                continue
            if defender_id == ai.current_target_id:
                continue
            # Check if defender is a predator (predators don't rescue)
            if self.world.has_component(defender_id, Predator):
                continue

            defender_dist = math.hypot(
                d_trans.x - target_trans.x, d_trans.y - target_trans.y
            )
            if defender_dist <= rescue_radius:
                # Defender nearby! Interrupt predation
                ai.current_target_id = cast(EntityID, -1)
                return Status.FAILURE

        # Lock both entities (stop movement)
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)
        if target_controller:
            target_controller.target_velocity = pymunk.Vec2d(0, 0)

        # Deal damage (assume 60 FPS tick rate, dt ~= 0.016)
        dt = 0.016
        damage = predator.dps * dt
        target_needs.health -= damage

        # Check if prey is consumed
        if target_needs.health <= 0:
            # Destroy prey entity
            self.world.delete_entity(ai.current_target_id)

            # Reduce predator hunger
            my_needs = self.world.get_component(self.entity_id, Needs)
            if my_needs:
                my_needs.hunger = max(0.0, my_needs.hunger - 50.0)

            ai.current_target_id = cast(EntityID, -1)
            return Status.SUCCESS

        return Status.RUNNING


class FleePredator(Action):
    """
    Action to flee from nearby predators.
    """

    def __init__(
        self,
        name="Flee Predator",
        entity_id=None,
        world=None,
        blackboard=None,
        speed: float = 150.0,
    ):
        super().__init__(name, entity_id, world, blackboard)
        self.speed = speed

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        my_trans = self.world.get_component(self.entity_id, Transform)
        controller = self.world.get_component(self.entity_id, MovementController)
        if not my_trans or not controller:
            return Status.FAILURE

        # Find nearest predator
        nearest_predator = None
        min_dist = float("inf")
        flee_start_dist = 200.0  # Start fleeing if predator is this close

        for uid, (pred, trans) in self.world.get_components_tuple(Predator, Transform):
            if uid == self.entity_id:
                continue

            dist = math.hypot(trans.x - my_trans.x, trans.y - my_trans.y)
            if dist < flee_start_dist and dist < min_dist:
                min_dist = dist
                nearest_predator = trans

        if nearest_predator:
            # Run away!
            # Vector from predator to me
            flee_vec = pymunk.Vec2d(
                my_trans.x - nearest_predator.x, my_trans.y - nearest_predator.y
            )
            if flee_vec.length > 0:
                # Use self.speed instead of controller.max_speed
                flee_vec = flee_vec.normalized() * self.speed
                controller.target_velocity = flee_vec
                return Status.RUNNING

        # Safe - return FAILURE so Selector continues to Normal Behavior
        return Status.FAILURE


class FindPrey(Action):
    """
    Finds a suitable prey target for a predator.
    """

    def __init__(self, name="Find Prey", entity_id=None, world=None, blackboard=None):
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        predator = self.world.get_component(self.entity_id, Predator)
        my_trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not predator or not my_trans:
            return Status.FAILURE

        # Find nearest valid prey
        best_target = -1
        min_dist = predator.prey_sense_radius

        # Iterate all needs-having entities (Candidate for optimization: Spatial Hash)
        for uid, (needs, trans) in self.world.get_components_tuple(Needs, Transform):
            if uid == self.entity_id:
                continue

            # Check if alive
            if needs.health <= 0:
                continue

            # Check tags/compatibility
            # For now, simple check: is it a yukkuri?
            # Ideally we check 'tags' component or type_id
            target_stats = self.world.try_get_component(uid, YukkuriStats)
            if not target_stats:
                continue

            # Predator-Prey Logic:
            # If I have 'prey_tags', check if target matches.
            # Simplified: Predators eat non-predators or smaller ones.
            # For this implementation, we assume any other yukkuri is prey
            # unless they are also a predator of same/higher level (?) through tags.

            # Use Predator component tags logic if implemented, else Fallback.
            # Fallback: Eat Reimu/Marisa if I am Predator.
            is_valid_prey = False
            if predator.prey_tags:
                # Todo: Check target tags. For now assume target type_id is a tag.
                if target_stats.type_id in predator.prey_tags:
                    is_valid_prey = True
            else:
                # Default behavior: Eat anyone who is NOT a predator
                if not self.world.has_component(uid, Predator):
                    is_valid_prey = True

            if is_valid_prey:
                dist = math.hypot(trans.x - my_trans.x, trans.y - my_trans.y)
                if dist < min_dist:
                    min_dist = dist
                    best_target = uid

        if best_target != -1:
            if ai.current_target_id != best_target:
                ai.current_target_id = cast(EntityID, best_target)
                ai.path = None
            return Status.SUCCESS

        return Status.FAILURE


class EatPrey(Action):
    """
    Channeling action to eat prey.
    """

    def __init__(self, name="Eat Prey", entity_id=None, world=None, blackboard=None):
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        predator = self.world.get_component(self.entity_id, Predator)
        trans = self.world.get_component(self.entity_id, Transform)
        controller = self.world.get_component(self.entity_id, MovementController)

        if not ai or not predator or not trans:
            return Status.FAILURE

        if ai.current_target_id == -1:
            return Status.FAILURE

        target_trans = self.world.try_get_component(ai.current_target_id, Transform)
        target_needs = self.world.try_get_component(ai.current_target_id, Needs)
        target_controller = self.world.try_get_component(
            ai.current_target_id, MovementController
        )

        if target_trans is None or target_needs is None:
            return Status.FAILURE

        # Check interaction distance
        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        if dist > 40.0:
            # Too far to eat!
            return Status.FAILURE

        # --- Social Defense (Rescue) Check ---
        rescue_radius = 60.0
        for defender_id, (d_stats, d_trans) in self.world.get_components_tuple(
            YukkuriStats, Transform
        ):
            if defender_id == self.entity_id:
                continue
            if defender_id == ai.current_target_id:
                continue
            if self.world.has_component(defender_id, Predator):
                continue

            defender_dist = math.hypot(
                d_trans.x - target_trans.x, d_trans.y - target_trans.y
            )
            if defender_dist <= rescue_radius:
                # Defender nearby! Interrupt predation
                ai.current_target_id = cast(EntityID, -1)
                return Status.FAILURE

        # Lock movement
        if controller:
            controller.target_velocity = pymunk.Vec2d(0, 0)
        if target_controller:
            target_controller.target_velocity = pymunk.Vec2d(0, 0)

        # Deal damage
        dt = 0.016  # Approximated fixed delta
        damage = predator.dps * dt
        target_needs.health -= damage

        # Visual feedback (Todo: Particles)

        # Check if consumed
        if target_needs.health <= 0:
            self.world.destroy_entity(ai.current_target_id)

            my_needs = self.world.try_get_component(self.entity_id, Needs)
            if my_needs:
                my_needs.hunger = max(0.0, my_needs.hunger - 50.0)

            ai.current_target_id = cast(EntityID, -1)
            return Status.SUCCESS

        return Status.RUNNING


class Swoop(Action):
    """
    Rapid descent to attack target.
    """

    def __init__(self, name="Swoop", entity_id=None, world=None, blackboard=None):
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        flight = self.world.try_get_component(self.entity_id, Flight)
        if not flight:
            return Status.FAILURE

        # Start swooping if not already
        if flight.state != FlightState.SWOOPING:
            flight.state = FlightState.SWOOPING
            flight.vertical_speed = 50.0  # Dive speed

        # Check altitude
        if flight.altitude <= 5.0:  # Close enough to ground
            flight.state = FlightState.GROUNDED
            flight.altitude = 0.0
            return Status.SUCCESS

        return Status.RUNNING


def build_hunt_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
    """
    Builds the behavior subtree for the 'Hunt' goal (Predator hunting prey).

    Args:
        entity_id (int): The entity ID.
        world (World): The ECS World.
        width (int): World width.
        height (int): World height.
        check_goal_fn (Callable): Checks if the goal is active.
        check_target_fn (Callable): Checks if a target is valid.

    Returns:
        Behaviour: The behavior tree for the goal.
    """
    # Root sequence for Hunting
    root = py_trees.composites.Sequence(name="Hunt Sequence", memory=True)

    # 1. Check Goal
    goal_check = Check(
        name="Check Hunt Goal",
        check_fn=lambda: check_goal_fn("Hunt"),
    )
    root.add_child(goal_check)

    # 2. Find Prey (if no target)
    find_prey = FindPrey(
        name="Find Prey", entity_id=entity_id, world=world, blackboard=None
    )
    root.add_child(find_prey)

    # 3. Approach and Strike (Selector: Aerial or Ground)
    approach_selector = py_trees.composites.Selector(
        name="Approach Strategy", memory=False
    )

    # 3a. Aerial Assault (if flying)
    # Check if we can fly
    def can_fly_check():
        f = world.try_get_component(entity_id, Flight)
        return f is not None and f.stamina > 20.0

    aerial_assault = py_trees.composites.Sequence(name="Aerial Assault", memory=True)
    aerial_assault.add_child(Check(name="Can Fly Check", check_fn=can_fly_check))
    # Fly to target (using air grid)
    aerial_assault.add_child(
        MoveToTarget(
            entity_id=entity_id,
            world=world,
            acceptance_radius=20.0,
            name="Fly To Target",
        )
    )
    # Swoop down
    aerial_assault.add_child(Swoop(entity_id=entity_id, world=world))

    approach_selector.add_child(aerial_assault)

    # 3b. Ground Assault (fallback)
    ground_assault = MoveToTarget(
        entity_id=entity_id, world=world, acceptance_radius=40.0, name="Chase Prey"
    )
    approach_selector.add_child(ground_assault)

    root.add_child(approach_selector)

    # 4. Eat Prey (Channeling)
    eat_prey = EatPrey(
        name="Eat Prey", entity_id=entity_id, world=world, blackboard=None
    )
    root.add_child(eat_prey)

    return root


# Register the Hunt behavior
BehaviorRegistry.register_goal("Hunt", build_hunt_behavior, required_component=Needs)
