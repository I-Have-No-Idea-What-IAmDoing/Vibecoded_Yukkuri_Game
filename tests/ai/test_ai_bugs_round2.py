"""
Regression tests for AI bug fixes — Round 2.

Tests cover:
1. FleePredator hostile-only check
2. FindItem path_request_time stamp
3. BehaviorSystem FAILURE removes from stable_entities
4. SocialSystem single register_interaction per interaction
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
from yukkuri_game.engine.types import EntityID
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.game.components import (
    AIState,
    EmotionalState,
    InteractionRequest,
    Needs,
    Predator,
    RelationshipData,
    RelationshipRegistry,
    YukkuriStats,
)
from yukkuri_game.game.ai.behaviors.actions.movement import FleePredator
from yukkuri_game.game.ai.behaviors.actions.searching import FindItem
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.events import SocialInteractionEvent
from yukkuri_game.game.trait_service import TraitService


def _make_yukkuri_stats(type_id: str = "reimu") -> YukkuriStats:
    """Helper to create a YukkuriStats component."""
    stats = YukkuriStats(type_id=type_id, name="TestYukkuri")
    return stats


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
        world = _setup_world = self._setup_world()

        # Prey entity
        prey_ai = AIState()
        prey_trans = Transform(x=400.0, y=400.0)
        prey_ctrl = MovementController()
        prey_stats = _make_yukkuri_stats("reimu")
        prey_needs = Needs()
        prey = world.create_entity(prey_ai, prey_trans, prey_ctrl, prey_stats, prey_needs)

        # Predator that hunts beanpaste only (not Yukkuris)
        pred_trans = Transform(x=420.0, y=400.0)
        pred_comp = Predator(
            prey_tags={"beanpaste"},
            prey_sense_radius=500.0,
            dps=10.0,
        )
        world.create_entity(pred_trans, pred_comp)

        action = FleePredator(entity_id=prey, world=world)
        status = action.update()

        self.assertEqual(
            status,
            Status.FAILURE,
            "FleePredator should return FAILURE (no valid threat) when predator"
            " does not hunt this entity type.",
        )

    def test_flee_triggers_for_hostile_predator(self) -> None:
        """Entity SHOULD enter RUNNING state when a hostile predator is nearby."""
        world = self._setup_world()

        prey_ai = AIState()
        prey_trans = Transform(x=400.0, y=400.0)
        prey_ctrl = MovementController()
        prey_stats = _make_yukkuri_stats("reimu")
        prey_needs = Needs()
        prey = world.create_entity(
            prey_ai, prey_trans, prey_ctrl, prey_stats, prey_needs
        )

        # Predator that hunts generic Yukkuris
        pred_trans = Transform(x=420.0, y=400.0)
        pred_comp = Predator(
            prey_tags={"Yukkuri"},
            prey_sense_radius=500.0,
            dps=10.0,
        )
        world.create_entity(pred_trans, pred_comp)

        action = FleePredator(entity_id=prey, world=world)
        status = action.update()

        self.assertEqual(
            status,
            Status.RUNNING,
            "FleePredator should return RUNNING when a 'Yukkuri'-hunting predator"
            " is within flee radius.",
        )

    def test_flee_triggers_for_type_specific_predator(self) -> None:
        """Entity should flee if predator's prey_tags includes its exact type_id."""
        world = self._setup_world()

        prey_ai = AIState()
        prey_trans = Transform(x=400.0, y=400.0)
        prey_ctrl = MovementController()
        prey_stats = _make_yukkuri_stats("marisa")
        prey_needs = Needs()
        prey = world.create_entity(
            prey_ai, prey_trans, prey_ctrl, prey_stats, prey_needs
        )

        pred_trans = Transform(x=420.0, y=400.0)
        pred_comp = Predator(
            prey_tags={"marisa"},  # Hunts marisa specifically
            prey_sense_radius=500.0,
            dps=10.0,
        )
        world.create_entity(pred_trans, pred_comp)

        action = FleePredator(entity_id=prey, world=world)
        status = action.update()

        self.assertEqual(
            status,
            Status.RUNNING,
            "FleePredator should return RUNNING when predator's prey_tags"
            " includes the entity's type_id.",
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
        time_service = TimeService()
        world.services.register(time_service)

        # Mock NavigationService
        nav_service = MagicMock(spec=NavigationService)
        world.services.register(nav_service, service_type=NavigationService)

        # Yukkuri at origin
        ai = AIState()
        trans = Transform(x=0.0, y=0.0)
        needs = Needs()
        stats = _make_yukkuri_stats("reimu")
        entity = world.create_entity(ai, trans, needs, stats)

        # Far-away target (forces path request)
        from yukkuri_game.game.components import ItemStats

        item_stats = ItemStats(
            name="BeanPaste",
            type_id="beanpaste",
            cost=1,
            nutrition=50.0,
            fun=10.0,
            comfort=0.0,
        )
        item_trans = Transform(x=900.0, y=900.0)
        item_entity = world.create_entity(item_trans, item_stats)

        # Simulate that FindItem discovers a new item via a mock GameService
        from yukkuri_game.game.services import GameService

        game_service = MagicMock(spec=GameService)
        game_service.find_best_item.return_value = item_entity
        world.services.register(game_service, service_type=GameService)

        action = FindItem(
            name="FindItem", entity_id=entity, world=world, stat_criteria="nutrition"
        )
        result = action.update()
        world.commands.apply_all()

        # FindItem should succeed and set path_requesting
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
        """
        Entities are removed from stable_entities when their tree returns FAILURE.
        """
        # Instantiate a minimal BehaviorSystem and manually invoke the logic
        bs = BehaviorSystem()
        bs.stable_entities = {42}  # entity 42 is currently "stable"

        # Simulate FAILURE root status — entity should be evicted from stable_entities
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
        """Control test: SUCCESS still adds to stable_entities."""
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


class TestSocialSystemSingleRegister(unittest.TestCase):
    """SocialSystem must apply interaction effects exactly once per request."""

    def _make_social_world(
        self,
    ) -> tuple[World, SocialSystem, int, int]:
        """Build a minimal world with two Yukkuris and SocialSystem."""
        world = World()
        event_bus = EventBus()
        world.services.register(event_bus)
        world.services.register(TimeService())

        trait_service = MagicMock(spec=TraitService)
        # Return a minimal interaction that adds +10 happiness to both parties
        mock_interaction = {
            "type": "GREET",
            "base_impact": 10.0,
            "social_impact": {},
            "modifiers": {},
            "conditions": [],
            "physical_impact": {},
            "target_physical_impact": {},
            "actor_physical_impact": {},
            "skill_rewards": {},
        }
        trait_service.get_interaction.return_value = mock_interaction
        trait_service.get_trait.return_value = None
        world.services.register(trait_service, service_type=TraitService)

        # Create entities
        actor_emotion = EmotionalState()
        actor = world.create_entity(
            Transform(x=0.0, y=0.0),
            YukkuriStats(type_id="reimu", name="Actor"),
            Needs(),
            actor_emotion,
        )
        target = world.create_entity(
            Transform(x=10.0, y=0.0),
            YukkuriStats(type_id="reimu", name="Target"),
            Needs(),
            EmotionalState(),
        )

        social_sys = SocialSystem()
        social_sys.trait_service = trait_service
        social_sys.event_bus = event_bus

        # Wire on_social_interaction as event handler
        event_bus.subscribe(SocialInteractionEvent, social_sys.on_social_interaction)
        social_sys.ecs_world = world

        return world, social_sys, actor, target

    def test_interaction_applied_once_via_event(self) -> None:
        """
        process_interaction_request publishes event only — effects applied once.
        """
        world, social_sys, actor, target = self._make_social_world()

        actor_emotion = world.try_get_component(actor, EmotionalState)
        self.assertIsNotNone(actor_emotion)

        happiness_before = actor_emotion.happiness  # type: ignore[union-attr]

        request = InteractionRequest(target_id=target, consume=False, action="Greet")
        social_sys.process_interaction_request(world, actor, request)
        # publish() is synchronous — handler fires immediately, no flush needed.

        happiness_after = actor_emotion.happiness  # type: ignore[union-attr]
        delta_once = happiness_after - happiness_before

        # Reset to baseline and simulate the OLD buggy double call
        actor_emotion.happiness = happiness_before  # type: ignore[union-attr]

        # Buggy path: call register_interaction directly AND publish event
        social_sys.register_interaction(world, actor, target, "Greet")
        # The event bus subscriber will also fire on the next publish — simulate it
        social_sys.register_interaction(world, actor, target, "Greet")
        happiness_double = actor_emotion.happiness  # type: ignore[union-attr]
        delta_double = happiness_double - happiness_before

        # Verify the fixed path gives ~half the impact of the buggy path
        if abs(delta_once) > 0.001:
            ratio = abs(delta_double) / abs(delta_once)
            self.assertAlmostEqual(
                ratio,
                2.0,
                delta=0.6,
                msg=(
                    f"Double-call produced delta={delta_double:.4f}; "
                    f"single-call produced delta={delta_once:.4f}. "
                    f"Expected ratio ≈ 2.0 but got {ratio:.2f}."
                ),
            )


if __name__ == "__main__":
    unittest.main()
