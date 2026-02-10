from typing import TYPE_CHECKING, Any, Callable

import py_trees
from py_trees.behaviour import Behaviour

from ...yukkuri_components import (
    AIState,
    ItemStats,
    Needs,
    Predator,
)
from ..utility_selector import UtilitySelector
from .actions.basic import Check, CheckEmotion, Idle
from .actions.interaction import EatPrey, Interact, SocialInteract
from .actions.movement import FleeFromTarget, FleePredator, MoveToTarget, Swoop, Wander
from .actions.searching import (
    FindItem,
    FindLightSource,
    FindPrey,
    FindSocialTarget,
    FindThreat,
    PickFood,
)
from .actions.survival import Sleep

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World


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
        return cls._goals

    @classmethod
    def get_target_requirement(cls, goal_name: str) -> type[Any] | None:
        return cls._target_requirements.get(goal_name)


def build_need_satisfaction_behavior(
    goal_name: str,
    find_action_class: type[Behaviour],
    interaction_action_class: type[Behaviour],
    stat_criteria: str | None = None,
    acceptance_radius: float = 50.0,
    consume_target: bool = False,
) -> Callable[
    [int, "World", int, int, Callable[[str], bool], Callable[[], bool]], Behaviour
]:
    """
    Factory that creates a behavior builder for standard need satisfaction loops.

    Pattern: Check Goal -> Sequence [Find Target -> Move To Target -> Interact]

    Args:
        goal_name (str): The name of the goal (e.g., "Eat", "Sleep").
        find_action_class (type[Behaviour]): Action class to find the target.
        interaction_action_class (type[Behaviour]): Action class to interact with target.
        stat_criteria (str | None): Criteria for finding target (e.g., "nutrition").
        acceptance_radius (float): Distance to stop from target.
        consume_target (bool): Whether interaction consumes the target.

    Returns:
        Callable[[int, World, int, int, Callable[[str], bool], Callable[[], bool]], Behaviour]: A builder function compatible with BehaviorRegistry.
    """

    def builder(
        entity_id: int,
        world: "World",
        width: int,
        height: int,
        check_goal_fn: Callable[[str], bool],
        check_target_fn: Callable[[], bool],
    ) -> Behaviour:
        sequence_name = f"{goal_name} Sequence"
        root = py_trees.composites.Sequence(name=sequence_name, memory=False)

        # 1. Check if this is the current goal
        is_goal = Check(
            name=f"Goal={goal_name}?", check_fn=lambda: check_goal_fn(goal_name)
        )

        # 2. Execution Sequence
        execution = py_trees.composites.Sequence(
            name=f"{goal_name} Execution", memory=False
        )

        # 2.1 Find Target
        find_kwargs = {
            "name": f"Find Best {goal_name} Target",
            "entity_id": entity_id,
            "world": world,
        }
        if stat_criteria:
            find_kwargs["stat_criteria"] = stat_criteria

        find_action = find_action_class(**find_kwargs)

        # 2.2 Move To Target
        move_action = MoveToTarget(
            name=f"Move To {goal_name} Target",
            entity_id=entity_id,
            world=world,
            acceptance_radius=acceptance_radius,
        )

        # 2.3 Interact
        interact_kwargs = {
            "name": f"Do {goal_name}",
            "entity_id": entity_id,
            "world": world,
        }
        # Only pass 'consume' if the class accepts it (Interact does, Sleep does not)
        if consume_target and interaction_action_class == Interact:
            interact_kwargs["consume"] = True
        elif interaction_action_class == Interact:
            interact_kwargs["consume"] = False

        interact_action = interaction_action_class(**interact_kwargs)

        execution.add_children([find_action, move_action, interact_action])
        root.add_children([is_goal, execution])
        return root

    return builder


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


def build_seek_light_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
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
    move_to_light = MoveToTarget(
        name="Move To Light", entity_id=entity_id, world=world, acceptance_radius=50.0
    )

    seek_execution.add_children([find_light, move_to_light])
    seek_sequence.add_children([is_seeking, seek_execution])
    return seek_sequence


def build_hunt_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
    root = py_trees.composites.Sequence(name="Hunt Sequence", memory=True)

    goal_check = Check(
        name="Check Hunt Goal",
        check_fn=lambda: check_goal_fn("Hunt"),
    )
    root.add_child(goal_check)

    find_prey = FindPrey(
        name="Find Prey", entity_id=entity_id, world=world, blackboard=None
    )
    root.add_child(find_prey)

    approach_selector = py_trees.composites.Selector(
        name="Approach Strategy", memory=False
    )

    from ...yukkuri_components import Flight

    def can_fly_check():
        f = world.try_get_component(entity_id, Flight)
        return f is not None and f.stamina > 20.0

    aerial_assault = py_trees.composites.Sequence(name="Aerial Assault", memory=True)
    aerial_assault.add_child(Check(name="Can Fly Check", check_fn=can_fly_check))
    aerial_assault.add_child(
        MoveToTarget(
            entity_id=entity_id,
            world=world,
            acceptance_radius=20.0,
            name="Fly To Target",
        )
    )
    aerial_assault.add_child(Swoop(entity_id=entity_id, world=world))
    approach_selector.add_child(aerial_assault)

    ground_assault = MoveToTarget(
        entity_id=entity_id, world=world, acceptance_radius=40.0, name="Chase Prey"
    )
    approach_selector.add_child(ground_assault)

    root.add_child(approach_selector)

    eat_prey = EatPrey(
        name="Eat Prey", entity_id=entity_id, world=world, blackboard=None
    )
    root.add_child(eat_prey)
    return root


def build_flee_behavior(
    entity_id: int,
    world: "World",
    width: int,
    height: int,
    check_goal_fn: Callable[[str], bool],
    check_target_fn: Callable[[], bool],
) -> Behaviour:
    root = py_trees.composites.Sequence(name="Flee Sequence", memory=True)
    root.add_child(Check(name="Goal=Flee?", check_fn=lambda: check_goal_fn("Flee")))
    root.add_child(FindThreat(name="Identify Threat", entity_id=entity_id, world=world))
    root.add_child(
        FleeFromTarget(name="Pick Run Spot", entity_id=entity_id, world=world)
    )
    root.add_child(
        MoveToTarget(
            name="Run!", entity_id=entity_id, world=world, acceptance_radius=50.0
        )
    )
    return root


def build_standard_interaction_behavior(goal_name: str):
    def builder(
        entity_id: int,
        world: "World",
        width: int,
        height: int,
        check_goal_fn: Callable[[str], bool],
        check_target_fn: Callable[[], bool],
    ) -> Behaviour:
        root = py_trees.composites.Sequence(name=f"{goal_name} Sequence", memory=True)

        root.add_child(
            Check(name=f"Goal={goal_name}?", check_fn=lambda: check_goal_fn(goal_name))
        )

        find_selector = py_trees.composites.Selector(
            name="Target Selector", memory=False
        )

        def has_valid_target():
            ai = world.try_get_component(entity_id, AIState)
            return ai and ai.current_target_id != -1

        find_selector.add_child(Check(name="Has Target?", check_fn=has_valid_target))

        if goal_name == "Eat":
            find_selector.add_child(PickFood(entity_id=entity_id, world=world))
        elif goal_name in ("Talk", "Dance"):
            find_selector.add_child(
                FindSocialTarget(
                    name=f"Find {goal_name} Partner",
                    entity_id=entity_id,
                    world=world,
                    criteria="friend",
                )
            )
        elif goal_name == "Fight":
            find_selector.add_child(
                FindSocialTarget(
                    name="Find Fight Target",
                    entity_id=entity_id,
                    world=world,
                    criteria="enemy",
                )
            )

        root.add_child(find_selector)

        root.add_child(
            MoveToTarget(
                name=f"Go to {goal_name} Target",
                entity_id=entity_id,
                world=world,
                acceptance_radius=30.0,
            )
        )

        if goal_name == "Eat":
            root.add_child(
                Interact(
                    name=f"Do {goal_name}",
                    entity_id=entity_id,
                    world=world,
                    consume=True,
                )
            )
        else:
            # Social Action
            root.add_child(
                SocialInteract(
                    name=f"Do {goal_name}",
                    entity_id=entity_id,
                    world=world,
                    interaction_type=goal_name,
                )
            )

        return root

    return builder


def create_yukkuri_behavior_tree(
    entity_id: int, world: "World", width: int, height: int
) -> py_trees.composites.Selector:
    def check_goal(goal_name: str) -> bool:
        ai = world.get_component(entity_id, AIState)
        if not ai:
            return False
        result = bool(ai.current_action == goal_name)
        return result

    def check_target_exists() -> bool:
        ai = world.get_component(entity_id, AIState)
        if not ai or ai.current_target_id == -1:
            return False
        from ...components import Transform

        has_trans = world.has_component(ai.current_target_id, Transform)
        if not has_trans:
            return False
        req_comp = BehaviorRegistry.get_target_requirement(ai.current_action)
        if req_comp:
            return world.has_component(ai.current_target_id, req_comp)
        return True

    root_selector = py_trees.composites.Selector(name="Root Selector", memory=False)

    # Stress Break
    stress_break = py_trees.composites.Sequence(name="Stress Break", memory=False)
    check_stress = CheckEmotion(
        name="High Stress?",
        entity_id=entity_id,
        world=world,
        check_fn=lambda e: e.stress > 90,
    )
    panic_action = Idle(name="Panic Freeze", entity_id=entity_id, world=world)
    stress_break.add_children([check_stress, panic_action])
    root_selector.add_child(stress_break)

    # Self Preservation
    flee_sequence = py_trees.composites.Sequence(name="Self Preservation", memory=False)
    flee_action = FleePredator(name="Flee Predator", entity_id=entity_id, world=world)
    flee_sequence.add_child(flee_action)
    root_selector.add_child(flee_sequence)

    # Normal Behavior
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


BehaviorRegistry.register_goal("Hunt", build_hunt_behavior, required_component=Predator)
BehaviorRegistry.register_goal("Wander", build_wander_behavior)
BehaviorRegistry.register_goal("SeekLight", build_seek_light_behavior)
BehaviorRegistry.register_goal("Flee", build_flee_behavior)

# Generic Need Satisfaction Behaviors
build_eat_behavior = build_need_satisfaction_behavior(
    "Eat", FindItem, Interact, "nutrition", 100.0, True
)

build_play_behavior = build_need_satisfaction_behavior(
    "Play", FindItem, Interact, "fun", 60.0, False
)

build_sleep_behavior = build_need_satisfaction_behavior(
    "Sleep", FindItem, Sleep, "comfort", 60.0, False
)

# Generic Need Satisfaction Registrations
BehaviorRegistry.register_goal(
    "Eat",
    build_eat_behavior,
    required_component=ItemStats,
)
BehaviorRegistry.register_goal(
    "Play",
    build_play_behavior,
    required_component=ItemStats,
)
BehaviorRegistry.register_goal(
    "Sleep",
    build_sleep_behavior,
    required_component=ItemStats,
)

BehaviorRegistry.register_goal("Talk", build_standard_interaction_behavior("Talk"))
BehaviorRegistry.register_goal("Dance", build_standard_interaction_behavior("Dance"))
BehaviorRegistry.register_goal("Fight", build_standard_interaction_behavior("Fight"))
