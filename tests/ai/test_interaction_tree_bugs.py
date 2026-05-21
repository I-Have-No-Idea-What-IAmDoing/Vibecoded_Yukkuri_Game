"""
Regression tests for the four interaction/tree bugs.

1. EatPrey returns FAILURE (not RUNNING) when prey exits melee range.
2. EatPrey scales damage by game_speed.
3. Aerial Assault re-evaluates Can Fly Check every tick (memory=False).
4. build_need_satisfaction_behavior wires check_target_fn into the sequence.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

import pymunk
from py_trees.common import Status

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.components import Transform, MovementController
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.components import (
    AIState,
    Needs,
    Predator,
    YukkuriStats,
)
from yukkuri_game.game.ai.behaviors.actions.interaction import EatPrey
from yukkuri_game.engine.types import EntityID


def _make_world() -> World:
    """Create a minimal world."""
    world = World()
    world.services.register(EventBus())
    ts = TimeService()
    world.services.register(ts)
    return world


class TestEatPreyOutOfRange(unittest.TestCase):
    """Bug 1: EatPrey must return FAILURE when prey is out of melee range."""

    def _make_predator(self, world: World, px: float, py: float) -> int:
        """Spawn a predator entity."""
        ai = AIState()
        trans = Transform(x=px, y=py)
        ctrl = MovementController()
        predator_comp = Predator(prey_tags={"Yukkuri"}, dps=10.0)
        needs = Needs()
        eid = world.create_entity(ai, trans, ctrl, predator_comp, needs)
        return eid

    def _make_prey(self, world: World, px: float, py: float) -> int:
        """Spawn a prey entity."""
        trans = Transform(x=px, y=py)
        needs = Needs(health=100.0)
        ctrl = MovementController()
        stats = YukkuriStats(name="Prey", type_id="reimu")
        eid = world.create_entity(trans, needs, ctrl, stats)
        return eid

    def test_returns_failure_when_prey_out_of_range(self) -> None:
        """EatPrey must return FAILURE (not RUNNING) when prey > 40 units away."""
        world = _make_world()
        predator = self._make_predator(world, 0.0, 0.0)
        prey = self._make_prey(world, 100.0, 0.0)  # 100 units away — out of 40u range

        ai = world.try_get_component(predator, AIState)
        assert ai is not None
        ai.current_target_id = EntityID(prey)

        action = EatPrey(entity_id=predator, world=world)
        action.initialise()
        status = action.update()

        self.assertEqual(
            status,
            Status.FAILURE,
            "EatPrey must return FAILURE when prey is out of melee range so the "
            "Hunt Sequence can reset and re-chase.",
        )

    def test_returns_running_when_prey_in_range(self) -> None:
        """EatPrey must return RUNNING while dealing damage within range."""
        world = _make_world()
        predator = self._make_predator(world, 0.0, 0.0)
        prey = self._make_prey(world, 10.0, 0.0)  # 10 units — within 40u range

        ai = world.try_get_component(predator, AIState)
        assert ai is not None
        ai.current_target_id = EntityID(prey)

        action = EatPrey(entity_id=predator, world=world)
        action.initialise()
        status = action.update()

        # Health should decrease and action should remain running
        prey_needs = world.try_get_component(prey, Needs)
        assert prey_needs is not None
        self.assertLess(
            prey_needs.health,
            100.0,
            "Prey health must decrease while EatPrey is in range.",
        )
        self.assertEqual(
            status,
            Status.RUNNING,
            "EatPrey should return RUNNING while prey is alive and in range.",
        )


class TestEatPreyGameSpeedScaling(unittest.TestCase):
    """Bug 2: EatPrey damage must scale with game_speed."""

    def _setup(
        self, game_speed: float
    ) -> tuple[World, int, int, EatPrey]:
        """Create a world with a specific game_speed setting."""
        world = _make_world()
        ts = world.services.get(TimeService)
        ts.game_speed = game_speed

        # Predator with fixed 10 dps
        ai = AIState()
        predator_comp = Predator(prey_tags={"Yukkuri"}, dps=10.0)
        needs = Needs()
        predator = world.create_entity(
            ai,
            Transform(x=0.0, y=0.0),
            MovementController(),
            predator_comp,
            needs,
        )

        # Prey in melee range
        prey_needs = Needs(max_health=1000.0, health=1000.0)
        prey = world.create_entity(
            Transform(x=5.0, y=0.0),
            prey_needs,
            MovementController(),
        )

        ai.current_target_id = EntityID(prey)

        action = EatPrey(entity_id=predator, world=world)
        action.initialise()
        return world, predator, prey, action

    def test_damage_scales_with_game_speed(self) -> None:
        """Damage at 2x speed must be roughly double damage at 1x speed."""
        world_1x, _, prey_1x, action_1x = self._setup(game_speed=1.0)
        action_1x.update()
        needs_1x = world_1x.try_get_component(prey_1x, Needs)
        assert needs_1x is not None
        damage_1x = 1000.0 - needs_1x.health

        world_2x, _, prey_2x, action_2x = self._setup(game_speed=2.0)
        action_2x.update()
        needs_2x = world_2x.try_get_component(prey_2x, Needs)
        assert needs_2x is not None
        damage_2x = 1000.0 - needs_2x.health

        self.assertGreater(damage_1x, 0.0, "Damage at 1x speed must be positive.")
        self.assertAlmostEqual(
            damage_2x,
            damage_1x * 2.0,
            delta=damage_1x * 0.1,  # ±10% tolerance
            msg=(
                f"Damage at 2x speed ({damage_2x:.4f}) should be ~2× "
                f"damage at 1x speed ({damage_1x:.4f})."
            ),
        )


class TestAerialAssaultMemory(unittest.TestCase):
    """Bug 3: Aerial Assault sequence must use memory=False."""

    def test_aerial_assault_has_memory_false(self) -> None:
        """The Aerial Assault sequence node must be memory=False."""
        import py_trees
        from yukkuri_game.game.ai.behaviors.trees import build_hunt_behavior

        world = _make_world()
        entity = world.create_entity(
            AIState(),
            Transform(x=0.0, y=0.0),
            Predator(prey_tags={"Yukkuri"}, dps=10.0),
            Needs(),
            YukkuriStats(name="Flandre", type_id="flandre"),
        )

        tree = build_hunt_behavior(
            entity_id=entity,
            world=world,
            width=3000,
            height=3000,
            check_goal_fn=lambda _: True,
            check_target_fn=lambda: True,
        )

        # Walk the tree to find the Aerial Assault node
        aerial_node = None
        for node in tree.iterate():
            if node.name == "Aerial Assault":
                aerial_node = node
                break

        self.assertIsNotNone(
            aerial_node, "Aerial Assault node must exist in the Hunt tree."
        )
        self.assertIsInstance(aerial_node, py_trees.composites.Sequence)
        self.assertFalse(
            aerial_node.memory,  # type: ignore[union-attr]
            "Aerial Assault must use memory=False so stamina is re-checked every tick.",
        )


class TestCheckTargetFnWired(unittest.TestCase):
    """Bug 4: build_need_satisfaction_behavior must include check_target_fn in execution."""

    def test_target_valid_check_is_in_tree(self) -> None:
        """The execution sequence must contain a 'Target Valid?' node."""
        from yukkuri_game.game.ai.behaviors.trees import (
            build_need_satisfaction_behavior,
        )
        from yukkuri_game.game.ai.behaviors.actions.interaction import Interact
        from yukkuri_game.game.ai.behaviors.actions.searching import FindItem

        world = _make_world()
        entity = world.create_entity(
            AIState(),
            Transform(x=0.0, y=0.0),
            Needs(),
            YukkuriStats(name="Reimu", type_id="reimu"),
        )

        builder = build_need_satisfaction_behavior(
            goal_name="Eat",
            find_action_class=FindItem,
            interaction_action_class=Interact,
            stat_criteria="nutrition",
            acceptance_radius=100.0,
            consume_target=True,
        )

        target_valid_calls: list[bool] = []

        def check_target() -> bool:
            target_valid_calls.append(True)
            return True

        tree = builder(
            entity_id=entity,
            world=world,
            width=3000,
            height=3000,
            check_goal_fn=lambda _: False,
            check_target_fn=check_target,
        )

        # Find node named "Target Valid?" anywhere in the tree
        target_valid_node = None
        for node in tree.iterate():
            if node.name == "Target Valid?":
                target_valid_node = node
                break

        self.assertIsNotNone(
            target_valid_node,
            "build_need_satisfaction_behavior must add a 'Target Valid?' "
            "Check node to the execution sequence.",
        )

    def test_target_invalid_stops_execution_before_move(self) -> None:
        """Returning False from check_target_fn should stop the execution sequence."""
        import py_trees as pt
        from yukkuri_game.game.ai.behaviors.trees import (
            build_need_satisfaction_behavior,
        )
        from yukkuri_game.game.ai.behaviors.actions.interaction import Interact
        from yukkuri_game.game.ai.behaviors.actions.searching import FindItem

        world = _make_world()
        entity = world.create_entity(
            AIState(),
            Transform(x=0.0, y=0.0),
            Needs(),
            YukkuriStats(name="Reimu", type_id="reimu"),
        )

        # Target is invalid — simulates entity destroyed mid-route
        def check_target() -> bool:
            return False

        builder = build_need_satisfaction_behavior(
            goal_name="Eat",
            find_action_class=FindItem,
            interaction_action_class=Interact,
            stat_criteria="nutrition",
            acceptance_radius=100.0,
            consume_target=True,
        )

        # goal is "active", but target is invalid
        tree = builder(
            entity_id=entity,
            world=world,
            width=3000,
            height=3000,
            check_goal_fn=lambda name: name == "Eat",
            check_target_fn=check_target,
        )
        tree.setup_with_descendants()

        from yukkuri_game.game.components import ItemStats
        from yukkuri_game.game.services import GameService

        # Give entity a current target so FindItem succeeds
        item = world.create_entity(
            Transform(x=5.0, y=0.0),
            ItemStats(name="BeanPaste", type_id="beanpaste", cost=1, nutrition=50.0),
        )
        ai = world.try_get_component(entity, AIState)
        assert ai is not None
        ai.current_action = "Eat"
        ai.current_target_id = EntityID(item)

        # Tick the tree — the Target Valid? check should stop execution
        tree.tick_once()
        # The tree should fail (not reach MoveToTarget or Interact)
        self.assertIn(
            tree.status,
            (Status.FAILURE, Status.INVALID),
            "Tree must not reach RUNNING/SUCCESS when check_target_fn returns False.",
        )


if __name__ == "__main__":
    unittest.main()
