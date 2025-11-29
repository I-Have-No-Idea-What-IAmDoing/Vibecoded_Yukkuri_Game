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
from ..yukkuri_components import AIState, ItemStats, YukkuriStats, EmotionalState, Personality
from ..trait_service import TraitService
from .base_action import Action
from .navigation_service import NavigationService
from .utility_selector import UtilitySelector

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World

def _is_brave(entity_id: int, world: "World") -> bool:
    """
    Helper to check if a yukkuri is brave (Bravery > 0).
    """
    personality = world.get_component(entity_id, Personality)
    if personality and personality.axis:
        return personality.axis.bravery > 0
    return False

# --- Behavior Tree Leaves (Actions) ---

class FindFood(Action):
    """
    Action to find food.
    If the entity has the PREDATOR trait (or 'can_eat_yukkuri' modifier),
    it will also consider other Yukkuris as food.
    """

    def __init__(self, name: str, entity_id: int, world: "World", stat_criteria: str = "nutrition"):
        super().__init__(name, entity_id, world)
        self.stat_criteria = stat_criteria

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or trans is None:
            return Status.FAILURE

        game_service = self.world.services.try_get(GameService)
        best_target = -1

        # 1. Look for Items
        if game_service:
            best_target = game_service.find_best_item(
                (trans.x, trans.y), self.stat_criteria, exclude_ids=ai.failed_targets
            )

        # 2. If Predator, look for Prey (Yukkuris)
        can_eat_yukkuri = False
        personality = self.world.get_component(self.entity_id, Personality)
        trait_service = self.world.services.try_get(TraitService)

        if personality and trait_service:
            # We need to check effective modifiers.
            overrides = personality.cached_overrides
            if overrides is None:
                 overrides = trait_service.calculate_overrides(personality.traits)
                 personality.cached_overrides = overrides # Cache the result

            if overrides and overrides.get("can_eat_yukkuri"):
                can_eat_yukkuri = True

        if can_eat_yukkuri:
            # Find closest Yukkuri (Prey)
            # TODO: Optimization: Use SectorSystem to avoid O(N) global scan
            nearby_yukkuris = self.world.get_entities_with(YukkuriStats, Transform)

            min_dist = float('inf')
            best_prey = -1

            for uid in nearby_yukkuris:
                if uid == self.entity_id: continue
                if uid in ai.failed_targets: continue

                u_trans = self.world.get_component(uid, Transform)
                if not u_trans: continue

                dist = math.hypot(u_trans.x - trans.x, u_trans.y - trans.y)
                if dist < min_dist:
                    min_dist = dist
                    best_prey = uid

            # If we found prey, compare with item (if any)
            if best_prey != -1:
                if best_target == -1:
                    best_target = best_prey
                else:
                    # Determine which is closer
                    # We need item position
                    item_trans = self.world.get_component(best_target, Transform)
                    if item_trans:
                        item_dist = math.hypot(item_trans.x - trans.x, item_trans.y - trans.y)
                        if min_dist < item_dist:
                            best_target = best_prey

        if best_target != -1:
            if ai.current_target_id != best_target:
                ai.current_target_id = best_target
                ai.path = None
            return Status.SUCCESS

        if ai.failed_targets:
            ai.failed_targets.clear()

        return Status.FAILURE


class MoveToTarget(Action):
    """
    Moves the entity towards a target using direct velocity control.
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
                if dist_to_final < self.acceptance_radius:
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    return Status.SUCCESS
                else:
                    ai.path = None
                    controller.target_velocity = pymunk.Vec2d(0, 0)
                    return Status.RUNNING

            next_point = pymunk.Vec2d(ai.path[0][0], ai.path[0][1])
            vector_to_next = next_point - current_pos

        # Calculate final velocity
        # Speed modifier based on Personality Energy (Active/Lazy)
        # Axis: -100 (Lazy) to 100 (Hyper)
        speed_modifier = 1.0
        personality = self.world.get_component(self.entity_id, Personality)
        if personality and personality.axis:
            # Map -100..100 to 0.5..1.5
            energy_val = personality.axis.energy
            speed_modifier = 1.0 + (energy_val / 200.0)

        # Also fatigue penalty from Stats.energy (Stamina)
        if stats.energy < 30:
            speed_modifier *= 0.5

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
            ai.path = None  # Reset path

        # Create a temporary MoveToTarget to handle the actual movement logic
        self.move_action = MoveToTarget(
            entity_id=self.entity_id, world=self.world, blackboard=self.blackboard
        )

    def update(self) -> Status:
        """
        Updates the move action.
        """
        if self.move_action:
            return self.move_action.update()
        return Status.FAILURE


class Interact(Action):
    """
    Handles interaction with a target entity (e.g., eating food).
    """

    def __init__(
        self,
        name: str = "Interact",
        entity_id: Optional[int] = None,
        world: Optional["World"] = None,
        blackboard: Optional[Any] = None,
        consume: bool = True,
    ):
        super().__init__(name, entity_id, world, blackboard)
        self.consume = consume

    def update(self) -> Status:
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
        if dist <= 30.0:  # Interaction range
            if not self.world.has_component(self.entity_id, InteractionRequest):
                self.world.add_component(
                    self.entity_id,
                    InteractionRequest(
                        target_id=ai.current_target_id, consume=self.consume
                    ),
                )
            return Status.SUCCESS

        return Status.RUNNING


class SocialInteract(Action):
    """
    Handles social interaction with another Yukkuri.
    """

    def __init__(
        self, name: str, entity_id: int, world: "World", interaction_type: str
    ):
        super().__init__(name, entity_id, world)
        self.interaction_type = interaction_type  # "Talk", "Fight", "Dance"

    def update(self) -> Status:
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
        if dist <= 40.0:
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
    """

    def __init__(self, name: str, entity_id: int, world: "World", criteria: str):
        super().__init__(name, entity_id, world)
        self.criteria = criteria  # "friend", "enemy", "any"

    def update(self) -> Status:
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

            if uid in ai.failed_targets:
                continue

            u_stats = self.world.get_component(uid, YukkuriStats)
            u_trans = self.world.get_component(uid, Transform)

            if u_stats is None or u_trans is None:
                continue

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
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        if self.world is None or self.entity_id is None:
            return Status.SUCCESS

        phys = self.world.get_component(self.entity_id, PhysicsBody)
        if phys:
            phys.body.velocity = (0, 0)
        return Status.SUCCESS


class Check(Action):
    """
    A behavior node that checks a condition function.
    """

    def __init__(self, name: str, check_fn: Callable[[], bool]):
        super().__init__(name)
        self.check_fn = check_fn

    def update(self) -> Status:
        if self.check_fn():
            return Status.SUCCESS
        return Status.FAILURE


class CheckEmotion(Action):
    """
    Checks the emotional state of the entity.
    """
    def __init__(self, name: str, entity_id: int, world: "World", check_fn: Callable[[EmotionalState], bool]):
        super().__init__(name, entity_id, world)
        self.check_fn = check_fn

    def update(self) -> Status:
        if not self.world or not self.entity_id: return Status.FAILURE
        emotion = self.world.get_component(self.entity_id, EmotionalState)
        if emotion and self.check_fn(emotion):
            return Status.SUCCESS
        return Status.FAILURE


class FindItem(Action):
    """
    Action to find an item based on criteria.
    """
    def __init__(self, name: str, entity_id: int, world: "World", stat_criteria: str):
        super().__init__(name, entity_id, world)
        self.stat_criteria = stat_criteria

    def update(self) -> Status:
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
                (trans.x, trans.y), self.stat_criteria, exclude_ids=ai.failed_targets
            )

        if best_item != -1:
            if ai.current_target_id != best_item:
                ai.current_target_id = best_item
                ai.path = None # Force re-pathing
            return Status.SUCCESS

        if ai.failed_targets:
            ai.failed_targets.clear()

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
        return cls._goals

    @classmethod
    def get_target_requirement(cls, goal_name: str) -> Optional[Type[Any]]:
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
    """
    eat_sequence = py_trees.composites.Sequence(name="Eat Sequence", memory=False)

    is_eating = Check(name="Goal=Eat?", check_fn=lambda: check_goal_fn("Eat"))

    eat_execution = py_trees.composites.Sequence(name="Eat Execution", memory=False)

    # FindFood will find the best food (Item or Prey).
    find_food = FindFood(
        name="Find Best Food", entity_id=entity_id, world=world, stat_criteria="nutrition"
    )

    move_to_food = MoveToTarget(
        name="Move To Food", entity_id=entity_id, world=world, acceptance_radius=30.0
    )
    interact_food = Interact(name="Interact Food", entity_id=entity_id, world=world)

    eat_execution.add_children([find_food, move_to_food, interact_food])
    eat_sequence.add_children([is_eating, eat_execution])
    return eat_sequence


def build_sleep_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
    sleep_sequence = py_trees.composites.Sequence(name="Sleep Sequence", memory=False)

    is_sleeping = Check(name="Goal=Sleep?", check_fn=lambda: check_goal_fn("Sleep"))
    sleep_execution = py_trees.composites.Sequence(name="Sleep Execution", memory=False)

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
    play_sequence = py_trees.composites.Sequence(name="Play Sequence", memory=False)

    is_playing = Check(name="Goal=Play?", check_fn=lambda: check_goal_fn("Play"))
    play_execution = py_trees.composites.Sequence(name="Play Execution", memory=False)

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
    """

    def check_goal(goal_name: str) -> bool:
        ai = world.get_component(entity_id, AIState)
        if not ai:
            return False
        return bool(ai.current_action == goal_name)

    def check_target_exists() -> bool:
        ai = world.get_component(entity_id, AIState)
        if not ai or ai.current_target_id == -1:
            return False

        has_trans = world.has_component(ai.current_target_id, Transform)
        if not has_trans:
            return False

        req_comp = BehaviorRegistry.get_target_requirement(ai.current_action)
        if req_comp:
            return world.has_component(ai.current_target_id, req_comp)

        return True

    root_selector = py_trees.composites.Selector(name="Root Selector", memory=False)

    stress_break = py_trees.composites.Sequence(name="Stress Break", memory=False)
    check_stress = CheckEmotion(
        name="High Stress?",
        entity_id=entity_id,
        world=world,
        check_fn=lambda e: e.stress > 90
    )

    # Response to Stress: Panic (Idle) or Rage (Wander/Fight)
    # Determined by Bravery axis.
    # We use a Selector to choose based on Personality.

    stress_response_selector = py_trees.composites.Selector(name="Stress Response Selector", memory=False)

    # Rage Path (Brave)
    rage_sequence = py_trees.composites.Sequence(name="Rage Sequence", memory=False)
    check_brave = Check(
        name="Is Brave?",
        check_fn=lambda: _is_brave(entity_id, world)
    )
    # Rage Action: For now, just Wander aggressively or similar.
    # Ideally, this would be "Attack anything nearby", but reusing Wander is safer fallback.
    # We can use Wander with high speed or specialized Rage behavior later.
    rage_action = Wander(name="Rage Wander", entity_id=entity_id, world=world, width=width, height=height)
    rage_sequence.add_children([check_brave, rage_action])

    # Panic Path (Default/Coward)
    panic_action = Idle(name="Panic Freeze", entity_id=entity_id, world=world)

    stress_response_selector.add_children([rage_sequence, panic_action])

    stress_break.add_children([check_stress, stress_response_selector])

    root_selector.add_child(stress_break)

    normal_behavior = py_trees.composites.Sequence(name="Normal Behavior", memory=False)

    utility_selector = UtilitySelector(entity_id=entity_id, world=world)
    normal_behavior.add_child(utility_selector)

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
