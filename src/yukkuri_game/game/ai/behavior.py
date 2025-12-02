"""
Module defining the behavior tree logic for AI agents.
"""

import math
import random
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, Tuple

import py_trees
import pymunk
from py_trees.behaviour import Behaviour
from py_trees.common import Status
from loguru import logger

from ...config import GameConfig
from ...engine.resource_manager import ResourceManager
from ..components import (
    InteractionRequest,
    MovementController,
    PhysicsBody,
    Transform,
    Velocity,
)
from ..services import GameService
from ..yukkuri_components import AIState, ItemStats, YukkuriStats, EmotionalState
from .base_action import Action
from .navigation_service import NavigationService
from .utility_selector import UtilitySelector

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
        entity_id: Optional[int] = None,
        world: Optional["World"] = None,
        blackboard: Optional[Any] = None,
        speed: float = 100.0,
        acceptance_radius: float = 15.0,
    ):
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
        stats = self.world.get_component(self.entity_id, YukkuriStats)
        controller = self.world.get_component(self.entity_id, MovementController)

        if ai is None or trans is None or stats is None or controller is None:
            return Status.FAILURE

        target_pos = None
        if ai.current_target_id != -1:
            target_trans = self.world.get_component(ai.current_target_id, Transform)
            if target_trans:
                target_pos = pymunk.Vec2d(target_trans.x, target_trans.y)
            else:
                ai.current_target_id = -1
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

        # Pathfinding (simplified)
        # Check if path needs (re)calculation.
        # This includes if path is empty, OR if we're moving to a dynamic target (entity)
        # and the target has moved significantly.
        # For now, just check if empty or None, but also ensure we don't assume empty path means success here.

        # NOTE: One issue might be that ai.path is empty because we just finished a path?
        # But if we are here, dist_to_final >= acceptance_radius. So we are NOT there yet.
        # So empty path means we need to find one.

        if ai.path is None or len(ai.path) == 0:
            nav_service = self.world.services.try_get(NavigationService)
            if nav_service:
                ai.path = nav_service.find_path((trans.x, trans.y), target_pos)

            if not ai.path:
                # Pathfinding failed. Mark target as failed to avoid loop.
                if ai.current_target_id != -1:
                    ai.failed_targets.add(ai.current_target_id)
                    ai.current_target_id = -1

                controller.target_velocity = pymunk.Vec2d(0, 0)
                return Status.FAILURE

        # Move along path
        next_point = pymunk.Vec2d(ai.path[0][0], ai.path[0][1])
        current_pos = pymunk.Vec2d(trans.x, trans.y)
        vector_to_next = next_point - current_pos
        dist_to_next = vector_to_next.length

        dist_to_final = (target_pos - current_pos).length
        if dist_to_final < self.acceptance_radius:
            controller.target_velocity = pymunk.Vec2d(0, 0)
            ai.path = []
            return Status.SUCCESS

        if dist_to_next < 15.0:  # Waypoint acceptance can remain small
            ai.path.pop(0)
            if not ai.path:
                # Path finished. Check if we are actually at the target.
                # If target moved or path was partial, we might not be there yet.
                if dist_to_final < self.acceptance_radius:
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    return Status.SUCCESS
                else:
                    # Not at target yet. Force path recalculation.
                    ai.path = None
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    return Status.RUNNING

            next_point = pymunk.Vec2d(ai.path[0][0], ai.path[0][1])
            vector_to_next = next_point - current_pos

        # Calculate final velocity
        # Simple speed modifier based on energy
        speed_modifier = 1.0
        if stats.energy < 30:
            speed_modifier = 0.5

        final_speed = self.speed * speed_modifier
        controller.target_velocity = vector_to_next.normalized() * final_speed

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
        entity_id: Optional[int] = None,
        world: Optional["World"] = None,
        blackboard: Optional[Any] = None,
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
        entity_id: Optional[int] = None,
        world: Optional["World"] = None,
        blackboard: Optional[Any] = None,
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
            # If animations are needed, we might need to wait, but for now immediate success matches previous behavior.
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
            game_service = self.world.services.try_get(GameService)
            if game_service:
                success = game_service.interact_social(
                    self.entity_id, ai.current_target_id, self.interaction_type
                )
                return Status.SUCCESS if success else Status.FAILURE

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
                ai.current_target_id = best_target
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
        entity_id: Optional[int] = None,
        world: Optional["World"] = None,
        blackboard: Optional[Any] = None,
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
    def __init__(self, name: str, entity_id: int, world: "World", check_fn: Callable[[EmotionalState], bool]):
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
        if not self.world or not self.entity_id: return Status.FAILURE
        emotion = self.world.get_component(self.entity_id, EmotionalState)
        if emotion and self.check_fn(emotion):
            return Status.SUCCESS
        return Status.FAILURE


# --- Behavior Tree Builder ---


class BehaviorRegistry:
    """
    Registry for behavior tree construction functions associated with high-level goals.
    """

    _goals: Dict[
        str,
        Callable[
            [int, "World", int, int, Callable[[str], bool], Callable[[], bool]],
            Behaviour,
        ],
    ] = {}
    _target_requirements: Dict[str, Type[Any]] = {}

    @classmethod
    def register_goal(
        cls,
        goal_name: str,
        builder: Callable[
            [int, "World", int, int, Callable[[str], bool], Callable[[], bool]],
            Behaviour,
        ],
        required_component: Optional[Type[Any]] = None,
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
    ) -> Dict[
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
    def get_target_requirement(cls, goal_name: str) -> Optional[Type[Any]]:
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
        name="Find Best Food", entity_id=entity_id, world=world, stat_criteria="nutrition"
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
                (trans.x, trans.y), self.stat_criteria, exclude_ids=ai.failed_targets, searcher_id=self.entity_id
            )

        if best_item != -1:
            # Only update and clear path if the target actually changed
            if ai.current_target_id != best_item:
                ai.current_target_id = best_item
                ai.path = None # Force re-pathing

            return Status.SUCCESS

        # If no item found, but we have ignored some targets (failed previously),
        # clear the failed list so we can retry them next frame.
        # This prevents the AI from starving if the only food source was momentarily unreachable.
        if ai.failed_targets:
            ai.failed_targets.clear()

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


# Register default behaviors
BehaviorRegistry.register_goal("Eat", build_eat_behavior, required_component=ItemStats)
BehaviorRegistry.register_goal("Sleep", build_sleep_behavior, required_component=ItemStats)
BehaviorRegistry.register_goal("Play", build_play_behavior, required_component=ItemStats)
BehaviorRegistry.register_goal("Wander", build_wander_behavior)
BehaviorRegistry.register_goal("Talk", build_talk_behavior, required_component=YukkuriStats)
BehaviorRegistry.register_goal("Fight", build_fight_behavior, required_component=YukkuriStats)
BehaviorRegistry.register_goal("Dance", build_dance_behavior, required_component=YukkuriStats)


def create_yukkuri_behavior_tree(
    entity_id: int, world: "World", width: int, height: int
) -> py_trees.composites.Sequence:
    """
    Builds the behavior tree for a Yukkuri.

    The tree structure uses a UtilitySelector to pick a goal, then executes that goal.
    It now includes a "Stress Break" high-priority sequence.

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

        has_trans = world.has_component(ai.current_target_id, Transform)
        if not has_trans:
            return False

        # Context-aware check using BehaviorRegistry metadata
        req_comp = BehaviorRegistry.get_target_requirement(ai.current_action)
        if req_comp:
            return world.has_component(ai.current_target_id, req_comp)

        return True

    # --- Root Sequence ---
    # 0. Stress Break (High Priority)
    # 1. Select Goal (UtilitySelector)
    # 2. Execute Goal (Selector)
    root = py_trees.composites.Sequence(name="Root Sequence", memory=False)

    # 0. Stress Break
    # If Stress > 90, force panic/tantrum. This should ideally interrupt everything else.
    # We can use a Selector at the top. If StressBreak succeeds (meaning we are stressed and doing panic),
    # the rest is skipped. Wait, Sequence runs all. We want a Selector for "Emergency vs Normal".

    # Let's restructure:
    # Root (Selector)
    #   -> Stress Break Sequence (Check Stress -> Panic Action)
    #   -> Normal Behavior Sequence (Utility -> Execution)

    root_selector = py_trees.composites.Selector(name="Root Selector", memory=False)

    stress_break = py_trees.composites.Sequence(name="Stress Break", memory=False)
    check_stress = CheckEmotion(
        name="High Stress?",
        entity_id=entity_id,
        world=world,
        check_fn=lambda e: e.stress > 90
    )
    # For now, panic is just Idle (freeze in terror) or maybe random movement later.
    # We can reuse Idle for "Freeze".
    panic_action = Idle(name="Panic Freeze", entity_id=entity_id, world=world)
    stress_break.add_children([check_stress, panic_action])

    root_selector.add_child(stress_break)

    # Normal Behavior
    normal_behavior = py_trees.composites.Sequence(name="Normal Behavior", memory=False)

    # 1. Utility Selector
    utility_selector = UtilitySelector(entity_id=entity_id, world=world)
    normal_behavior.add_child(utility_selector)

    # 2. Execution Selector
    execution_selector = py_trees.composites.Selector(
        name="Execution Selector", memory=False
    )

    goals = BehaviorRegistry.get_goals()

    for name, builder in goals.items():
        execution_selector.add_child(
            builder(entity_id, world, width, height, check_goal, check_target_exists)
        )

    idle = Idle(entity_id=entity_id, world=world)
    execution_selector.add_child(idle)

    normal_behavior.add_child(execution_selector)
    root_selector.add_child(normal_behavior)

    return root_selector
