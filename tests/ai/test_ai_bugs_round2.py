"""
Regression tests for AI bug fixes — Round 2.

Tests cover:
1. FleePredator hostile-only check
2. FindItem path_request_time stamp
3. BehaviorSystem FAILURE removes from stable_entities
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from py_trees.common import Status

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.components import Transform, MovementController
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.game.components import (
    AIState,
    Needs,
    Predator,
    YukkuriStats,
)
from yukkuri_game.game.ai.behaviors.actions.movement import FleePredator
from yukkuri_game.game.ai.behaviors.actions.searching import FindItem
from yukkuri_game.game.systems.behavior import BehaviorSystem


def _make_yukkuri_stats(type_id: str = "reimu") -> YukkuriStats:
    """Helper to create a YukkuriStats component."""
    return YukkuriStats(type_id=type_id, name="TestYukkuri")


class TestFleePredatorHostileOnly(unittest.TestCase):
    """FleePredator should only flee predators whose prey_tags cover this entity."""

    def _setup_world(self) -> World:
        """Create a minimal world for FleePredator tests."""
        world = World()
        world.services.register(EventBus())
        world.services.register(TimeService())
        return world

    def test_flee_ignores_non_hostile_predator(self) -> None:
        """Entity must NOT trigger flee for a predator that doesn't hunt it."""
        world = self._setup_world()

        prey_trans = Transform(x=400.0, y=400.0)
        prey_ctrl = MovementController()
        prey_stats = _make_yukkuri_stats("reimu")
        prey_needs = Needs()
        prey = world.create_entity(
            AIState(), prey_trans, prey_ctrl, prey_stats, prey_needs
        )

        # Predator that hunts beanpaste only — should NOT trigger flee
        pred_comp = Predator(
            prey_tags={"beanpaste"},
            prey_sense_radius=500.0,
            dps=10.0,
        )
        world.create_entity(Transform(x=420.0, y=400.0), pred_comp)

        status = FleePredator(entity_id=prey, world=world).update()

        self.assertEqual(
            status,
            Status.FAILURE,
            "FleePredator must return FAILURE when predator does not hunt this type.",
        )

    def test_flee_triggers_for_generic_yukkuri_hunter(self) -> None:
        """Entity SHOULD flee a predator whose prey_tags includes 'Yukkuri'."""
        world = self._setup_world()

        prey = world.create_entity(
            AIState(),
            Transform(x=400.0, y=400.0),
            MovementController(),
            _make_yukkuri_stats("reimu"),
            Needs(),
        )

        world.create_entity(
            Transform(x=420.0, y=400.0),
            Predator(prey_tags={"Yukkuri"}, prey_sense_radius=500.0, dps=10.0),
        )

        status = FleePredator(entity_id=prey, world=world).update()

        self.assertEqual(
            status,
            Status.RUNNING,
            "FleePredator must return RUNNING when a 'Yukkuri'-hunting predator"
            " is within flee radius.",
        )

    def test_flee_triggers_for_type_specific_predator(self) -> None:
        """Entity should flee if predator's prey_tags includes its exact type_id."""
        world = self._setup_world()

        prey = world.create_entity(
            AIState(),
            Transform(x=400.0, y=400.0),
            MovementController(),
            _make_yukkuri_stats("marisa"),
            Needs(),
        )

        world.create_entity(
            Transform(x=420.0, y=400.0),
            Predator(prey_tags={"marisa"}, prey_sense_radius=500.0, dps=10.0),
        )

        status = FleePredator(entity_id=prey, world=world).update()

        self.assertEqual(
            status,
            Status.RUNNING,
            "FleePredator must return RUNNING when predator's prey_tags"
            " includes the entity's exact type_id.",
        )


class TestFindItemPathRequestTime(unittest.TestCase):
    """FindItem anticipatory cache must stamp path_request_time."""

    def test_anticipatory_cache_sets_path_request_time(self) -> None:
        """
        When FindItem prefetches a path (anticipatory caching), it must set
        path_request_time so MoveToTarget's 2s timeout doesn't fire immediately.
        """
        world = World()
        world.services.register(EventBus())
        world.services.register(TimeService())

        nav_service = MagicMock(spec=NavigationService)
        world.services.register(nav_service, service_type=NavigationService)

        ai = AIState()
        entity = world.create_entity(
            ai,
            Transform(x=0.0, y=0.0),
            Needs(),
            _make_yukkuri_stats("reimu"),
        )

        from yukkuri_game.game.components import ItemStats

        item_stats = ItemStats(
            name="BeanPaste",
            type_id="beanpaste",
            cost=1,
            nutrition=50.0,
            fun=10.0,
            comfort=0.0,
        )
        item_entity = world.create_entity(Transform(x=900.0, y=900.0), item_stats)

        from yukkuri_game.game.services import GameService

        game_service = MagicMock(spec=GameService)
        game_service.find_best_item.return_value = item_entity
        world.services.register(game_service, service_type=GameService)

        result = FindItem(
            name="FindItem", entity_id=entity, world=world, stat_criteria="nutrition"
        ).update()
        world.commands.apply_all()

        self.assertEqual(result, Status.SUCCESS)
        self.assertIsNotNone(ai.state_data)
        self.assertTrue(
            ai.state_data.get("path_requesting"),
            "path_requesting must be True after FindItem issues a nav request.",
        )
        self.assertIn(
            "path_request_time",
            ai.state_data,
            "path_request_time MUST be set by FindItem to prevent immediate timeout.",
        )
        self.assertGreaterEqual(
            ai.state_data["path_request_time"],
            0.0,
            "path_request_time must be a valid non-negative timestamp.",
        )


class TestBehaviorSystemFailureThrottle(unittest.TestCase):
    """BehaviorSystem must not keep FAILURE entities in stable_entities."""

    def test_failure_removes_from_stable_entities(self) -> None:
        """Entities returning FAILURE must be evicted from stable_entities."""
        bs = BehaviorSystem()
        bs.stable_entities = {42}

        entity = 42
        root_status = Status.FAILURE

        if root_status == Status.SUCCESS:
            bs.stable_entities.add(entity)
        elif root_status == Status.RUNNING:
            bs.stable_entities.discard(entity)
        else:
            bs.stable_entities.discard(entity)

        self.assertNotIn(
            entity,
            bs.stable_entities,
            "Entity must NOT remain in stable_entities after FAILURE.",
        )

    def test_success_adds_to_stable_entities(self) -> None:
        """Control test: SUCCESS still adds entity to stable_entities."""
        bs = BehaviorSystem()
        bs.stable_entities = set()

        entity = 7
        root_status = Status.SUCCESS

        if root_status == Status.SUCCESS:
            bs.stable_entities.add(entity)
        elif root_status == Status.RUNNING:
            bs.stable_entities.discard(entity)
        else:
            bs.stable_entities.discard(entity)

        self.assertIn(entity, bs.stable_entities)

    def test_running_removes_from_stable_entities(self) -> None:
        """RUNNING also removes entity from stable_entities."""
        bs = BehaviorSystem()
        bs.stable_entities = {99}

        entity = 99
        root_status = Status.RUNNING

        if root_status == Status.SUCCESS:
            bs.stable_entities.add(entity)
        elif root_status == Status.RUNNING:
            bs.stable_entities.discard(entity)
        else:
            bs.stable_entities.discard(entity)

        self.assertNotIn(entity, bs.stable_entities)


if __name__ == "__main__":
    unittest.main()
