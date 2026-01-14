"""
Tests for improved social context calculation in UtilitySelector.
"""

import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import (
    YukkuriStats,
    Needs,
    AIState,
    Predator,
    RelationshipRegistry,
    RelationshipData,
)
from yukkuri_game.game.components import Transform
from yukkuri_game.game.ai.utility_selector import UtilitySelector
from yukkuri_game.game.ai.utility import UtilityAIEngine


class TestSocialContext:
    @pytest.fixture
    def world(self):
        w = World()
        # Register mock engine
        engine = UtilityAIEngine(MagicMock())
        w.services.register(engine, UtilityAIEngine)
        return w

    def create_yukkuri(self, world, type_id, x, y, is_predator=False, prey_tags=None):
        e = world.create_entity()
        world.add_component(e, Transform(x=x, y=y))
        world.add_component(e, YukkuriStats(name=type_id, type_id=type_id))
        world.add_component(e, Needs(energy=100))
        world.add_component(e, AIState())
        world.add_component(e, RelationshipRegistry())

        if is_predator:
            world.add_component(
                e, Predator(prey_tags=prey_tags or set(), prey_sense_radius=300)
            )

        return e

    def test_same_type_is_friend(self, world):
        """Same type entities should be friends by default."""
        me = self.create_yukkuri(world, "reimu", 0, 0)
        friend = self.create_yukkuri(world, "reimu", 50, 0)  # Nearby

        selector = UtilitySelector(entity_id=me, world=world)
        selector.engine = world.services.try_get(UtilityAIEngine)

        captured_context = {}

        def capture(context, *args):
            nonlocal captured_context
            captured_context = context
            return "Idle"

        selector.engine.select_action = capture
        selector.update()

        assert captured_context["nearby_friends"] == 1.0
        assert captured_context["nearby_enemies"] == 0.0

    def test_diff_type_is_neutral(self, world):
        """Different type entities should be neutral (not enemy) by default."""
        me = self.create_yukkuri(world, "reimu", 0, 0)
        other = self.create_yukkuri(world, "marisa", 50, 0)

        selector = UtilitySelector(entity_id=me, world=world)
        selector.engine = world.services.try_get(UtilityAIEngine)

        captured_context = {}
        selector.engine.select_action = lambda c, *a: (
            captured_context.update(c) or "Idle"
        )
        selector.update()

        # New behavior: neither friend nor enemy
        assert captured_context["nearby_friends"] == 0.0
        assert captured_context["nearby_enemies"] == 0.0

    def test_high_affinity_is_friend(self, world):
        """High affinity makes diff type a friend."""
        me = self.create_yukkuri(world, "reimu", 0, 0)
        other = self.create_yukkuri(world, "marisa", 50, 0)

        # Add high affinity
        reg = world.get_component(me, RelationshipRegistry)
        reg.relationships[other] = RelationshipData(affinity=50.0)

        selector = UtilitySelector(entity_id=me, world=world)
        selector.engine = world.services.try_get(UtilityAIEngine)

        captured_context = {}
        selector.engine.select_action = lambda c, *a: (
            captured_context.update(c) or "Idle"
        )
        selector.update()

        assert captured_context["nearby_friends"] == 1.0
        assert captured_context["nearby_enemies"] == 0.0

    def test_low_affinity_is_enemy(self, world):
        """Low affinity makes same/diff type an enemy."""
        me = self.create_yukkuri(world, "reimu", 0, 0)
        other = self.create_yukkuri(world, "reimu", 50, 0)  # Same type!

        # Add low affinity
        reg = world.get_component(me, RelationshipRegistry)
        reg.relationships[other] = RelationshipData(affinity=-50.0)

        selector = UtilitySelector(entity_id=me, world=world)
        selector.engine = world.services.try_get(UtilityAIEngine)

        captured_context = {}
        selector.engine.select_action = lambda c, *a: (
            captured_context.update(c) or "Idle"
        )
        selector.update()

        assert captured_context["nearby_friends"] == 0.0
        assert captured_context["nearby_enemies"] == 1.0

    def test_predator_sees_prey_as_enemy(self, world):
        """Predator should see prey as enemy (target)."""
        # Flandre (predator) vs Reimu (prey)
        me = self.create_yukkuri(
            world, "flandre", 0, 0, is_predator=True, prey_tags={"reimu"}
        )
        prey = self.create_yukkuri(world, "reimu", 50, 0)

        selector = UtilitySelector(entity_id=me, world=world)
        selector.engine = world.services.try_get(UtilityAIEngine)

        captured_context = {}
        selector.engine.select_action = lambda c, *a: (
            captured_context.update(c) or "Idle"
        )
        selector.update()

        # Should be enemy (for hunting)
        assert captured_context["nearby_enemies"] == 1.0

    def test_prey_sees_predator_as_enemy(self, world):
        """Prey should see predator as enemy (threat)."""
        me = self.create_yukkuri(world, "reimu", 0, 0)
        pred = self.create_yukkuri(
            world, "flandre", 50, 0, is_predator=True, prey_tags={"reimu"}
        )

        selector = UtilitySelector(entity_id=me, world=world)
        selector.engine = world.services.try_get(UtilityAIEngine)

        captured_context = {}
        selector.engine.select_action = lambda c, *a: (
            captured_context.update(c) or "Idle"
        )
        selector.update()

        assert captured_context["nearby_enemies"] == 1.0
