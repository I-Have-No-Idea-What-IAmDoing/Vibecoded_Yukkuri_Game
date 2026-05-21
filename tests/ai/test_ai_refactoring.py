"""
Tests verifying the Yukkuri AI refactoring behavior.

Includes tests for lifecycle cleanup hooks, navigation decoupling,
tag-based taxonomy matching, and compensated utility AI scoring.
"""

import unittest
from unittest.mock import MagicMock
import pymunk
import py_trees
from py_trees.common import Status

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.components import (
    MovementController,
    PhysicsBody,
    Transform,
)
from yukkuri_game.engine.data_models import (
    AIAction,
    ActionConsideration,
    ActionEffect,
)
from yukkuri_game.game.components import (
    AIState,
    ItemStats,
    MoveCommand,
    Needs,
    Predator,
    YukkuriStats,
)
from yukkuri_game.game.ai.behaviors.actions.movement import (
    MoveToTarget,
    FleePredator,
)
from yukkuri_game.game.ai.behaviors.actions.searching import FindPrey
from yukkuri_game.game.ai.utility import UtilityAIEngine


class MockResourceManager:
    """
    Mock resource manager for utility action loading.
    """

    def __init__(self, actions_data: dict[str, AIAction]) -> None:
        """
        Initializes MockResourceManager.

        Args:
            actions_data (dict[str, AIAction]): Mocked action data.
        """
        self.ai_actions = actions_data


class TestAIRefactoring(unittest.TestCase):
    """
    Integration and regression tests for Yukkuri AI refactorings.
    """

    def setUp(self) -> None:
        """
        Set up common test components.
        """
        self.world = World()
        self.entity_id = self.world.create_entity()

        # Add mandatory components
        self.world.add_component(self.entity_id, Transform(x=0.0, y=0.0))
        self.world.add_component(self.entity_id, AIState())
        self.world.add_component(self.entity_id, Needs(energy=100.0))
        self.world.add_component(self.entity_id, MovementController())

        # Initialize Blackboard for py_trees
        py_trees.blackboard.Blackboard().set("dt", 0.1)

    def test_lifecycle_cleanup_hook(self) -> None:
        """
        Verifies that terminate() invokes on_cleanup() correctly.
        """
        # Spawns movement commands
        self.world.commands.add_component(
            self.entity_id, MoveCommand(target_pos=pymunk.Vec2d(100, 100))
        )
        self.world.commands.apply_all()
        self.assertTrue(self.world.has_component(self.entity_id, MoveCommand))

        controller = self.world.get_component(
            self.entity_id, MovementController
        )
        controller.target_velocity = pymunk.Vec2d(50, 50)

        action = MoveToTarget(entity_id=self.entity_id, world=self.world)
        # Transition out of RUNNING
        action.terminate(Status.SUCCESS)
        self.world.commands.apply_all()

        self.assertFalse(self.world.has_component(self.entity_id, MoveCommand))
        self.assertEqual(controller.target_velocity, pymunk.Vec2d(0, 0))

    def test_flee_predator_cleanup_hook(self) -> None:
        """
        Verifies that FleePredator clears velocities on cleanup.
        """
        controller = self.world.get_component(
            self.entity_id, MovementController
        )
        controller.target_velocity = pymunk.Vec2d(120, 120)

        action = FleePredator(entity_id=self.entity_id, world=self.world)
        action.terminate(Status.FAILURE)

        self.assertEqual(controller.target_velocity, pymunk.Vec2d(0, 0))

    def test_navigation_decoupling_los_direct(self) -> None:
        """
        Verifies MoveToTarget update delegates to NavigationController.
        """
        # Configure a direct steering target (close-range, < 150m)
        ai = self.world.get_component(self.entity_id, AIState)
        ai.state_data = {"target_x": 50.0, "target_y": 0.0}

        action = MoveToTarget(
            entity_id=self.entity_id,
            world=self.world,
            speed=100.0,
            acceptance_radius=10.0,
        )
        status = action.update()
        self.world.commands.apply_all()

        self.assertEqual(status, Status.RUNNING)
        self.assertTrue(self.world.has_component(self.entity_id, MoveCommand))
        cmd = self.world.get_component(self.entity_id, MoveCommand)
        self.assertEqual(cmd.target_pos, pymunk.Vec2d(50.0, 0.0))

    def test_tag_based_taxonomy_matching(self) -> None:
        """
        Verifies FindPrey checks nutrition and tags case-insensitively.
        """
        # Spawns a predator
        self.world.add_component(
            self.entity_id,
            Predator(prey_tags={"Food", "Cookie"}, prey_sense_radius=500.0),
        )

        # Spawns a generic food item
        food_id = self.world.create_entity()
        self.world.add_component(food_id, Transform(x=100.0, y=0.0))
        self.world.add_component(
            food_id,
            ItemStats(
                name="Delicious Sweet",
                type_id="cookie",
                cost=10,
                nutrition=50.0,
            ),
        )

        action = FindPrey(entity_id=self.entity_id, world=self.world)
        status = action.update()

        self.assertEqual(status, Status.SUCCESS)
        ai = self.world.get_component(self.entity_id, AIState)
        self.assertEqual(ai.current_target_id, food_id)

    def test_compensated_utility_scoring(self) -> None:
        """
        Verifies geometric mean utility scoring prevents collapse.
        """
        mock_actions = {
            "MultiCon": AIAction(
                weight=1.0,
                effects=ActionEffect(type="test", stat_changes={}),
                considerations=[
                    ActionConsideration(
                        name="C1",
                        input="v1",
                        curve="linear",
                        params={"m": 1.0, "b": 0.0},
                    ),
                    ActionConsideration(
                        name="C2",
                        input="v2",
                        curve="linear",
                        params={"m": 1.0, "b": 0.0},
                    ),
                    ActionConsideration(
                        name="C3",
                        input="v3",
                        curve="linear",
                        params={"m": 1.0, "b": 0.0},
                    ),
                ],
            )
        }
        rm = MockResourceManager(mock_actions)
        engine = UtilityAIEngine(rm)

        # Input values of 50.0 normalize to v = 0.5
        context = {"v1": 50.0, "v2": 50.0, "v3": 50.0}

        # Multiplicative: 1.0 * 0.5 * 0.5 * 0.5 = 0.125
        mult_score = engine.actions["MultiCon"].calculate_utility(context)
        self.assertAlmostEqual(mult_score, 0.125, places=5)

        # Geometric Mean: 1.0 * (0.5 * 0.5 * 0.5) ** (1/3) = 0.5
        comp_score = engine.actions["MultiCon"].calculate_utility_compensated(
            context
        )
        self.assertAlmostEqual(comp_score, 0.5, places=5)

        # select_action uses compensated scoring by default now
        self.assertEqual(engine.select_action(context), "MultiCon")


if __name__ == "__main__":
    unittest.main()
